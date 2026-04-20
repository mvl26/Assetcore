<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { frappeGet } from '@/api/helpers'
import { computeDepreciation, type DepreciationResult } from '@/api/imm00'

interface DeprecRow {
  name: string
  asset_name: string
  purchase_date?: string
  gross_purchase_amount?: number
  depreciation_method?: string
  useful_life_years?: number
  accumulated_depreciation?: number
  current_book_value?: number
}

const rows = ref<DeprecRow[]>([])
const total = ref(0)
const loading = ref(false)
const running = ref<string | null>(null)
const msg = ref('')

const BASE = '/api/method/assetcore.api.imm00'

async function load() {
  loading.value = true
  try {
    const r = await frappeGet<{ items: DeprecRow[]; pagination: { total: number } } | null>(
      `${BASE}.list_assets`, { page: 1, page_size: 100 },
    )
    if (r) {
      const items = (r as unknown as { items: DeprecRow[] }).items || []
      // enrich with extra fields via individual calls is expensive — rely on list to include needed fields
      rows.value = items
      total.value = (r as unknown as { pagination: { total: number } }).pagination?.total || items.length
    }
  } finally { loading.value = false }
}

async function compute(name: string) {
  running.value = name; msg.value = ''
  try {
    const r = await computeDepreciation(name)
    const d = r as unknown as DepreciationResult
    if (d) msg.value = `${name}: lũy kế ${format(d.accumulated)} · còn lại ${format(d.book_value)} (${d.method || d.note || ''})`
    await load()
  } catch (e: unknown) { msg.value = (e as Error).message || 'Lỗi tính khấu hao' }
  finally { running.value = null }
}

async function computeAll() {
  if (!confirm(`Tính lại khấu hao cho ${rows.value.length} thiết bị?`)) return
  for (const r of rows.value) {
    try { await computeDepreciation(r.name) } catch { /* skip */ }
  }
  await load()
  msg.value = 'Đã tính lại khấu hao cho toàn bộ thiết bị.'
}

function format(v?: number) {
  return v != null ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v) : '—'
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-800">Khấu hao thiết bị</h1>
        <p class="text-xs text-gray-500 mt-0.5">Tính khấu hao theo phương pháp đường thẳng hoặc số dư giảm dần.</p>
      </div>
      <button @click="computeAll" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Tính lại toàn bộ</button>
    </div>

    <div v-if="msg" class="bg-blue-50 text-blue-800 text-sm p-3 rounded-lg">{{ msg }}</div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã TS</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên thiết bị</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500">Nguyên giá</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phương pháp</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tuổi thọ (năm)</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500">Khấu hao lũy kế</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500">Giá trị còn lại</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="a in rows" :key="a.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs">{{ a.name }}</td>
            <td class="px-4 py-3 font-medium">{{ a.asset_name }}</td>
            <td class="px-4 py-3 text-right">{{ format(a.gross_purchase_amount) }}</td>
            <td class="px-4 py-3 text-xs">{{ a.depreciation_method || '—' }}</td>
            <td class="px-4 py-3 text-xs">{{ a.useful_life_years || '—' }}</td>
            <td class="px-4 py-3 text-right text-gray-600">{{ format(a.accumulated_depreciation) }}</td>
            <td class="px-4 py-3 text-right font-semibold">{{ format(a.current_book_value) }}</td>
            <td class="px-4 py-3 text-right">
              <button @click="compute(a.name)" :disabled="running === a.name"
                class="text-blue-600 hover:text-blue-800 text-xs font-medium disabled:opacity-50">
                {{ running === a.name ? 'Đang tính...' : 'Tính' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
