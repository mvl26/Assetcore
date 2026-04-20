<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet, frappePost } from '@/api/helpers'
import type { AssetTransfer } from '@/types/imm00'

const router = useRouter()

const transfers = ref<AssetTransfer[]>([])
const loading = ref(false)
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 30
const error = ref('')

const BASE = '/api/method/assetcore.api.imm00'

const TYPE_COLORS: Record<string, string> = {
  Internal: 'bg-blue-100 text-blue-700',
  Loan: 'bg-yellow-100 text-yellow-700',
  External: 'bg-purple-100 text-purple-700',
  Return: 'bg-green-100 text-green-700',
}

async function load() {
  loading.value = true
  const res = await frappeGet<{ items: AssetTransfer[]; pagination: { total: number } } | null>(
    `${BASE}.list_transfers`,
    { page: page.value, page_size: PAGE_SIZE },
  )
  loading.value = false
  if (res) {
    transfers.value = res.items || []
    totalCount.value = res.pagination?.total || 0
  }
}

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; load() } }

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

async function remove(name: string) {
  if (!confirm(`Xóa chuyển giao ${name}?\n\nThao tác sẽ cancel nếu đã submit.`)) return
  try {
    await frappePost<void>(`${BASE}.delete_transfer`, { name })
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Xóa thất bại'
  }
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Chuyển giao thiết bị</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ totalCount }} lượt chuyển</span>
        <button @click="router.push('/asset-transfers/new')" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Tạo mới</button>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 border border-red-300 text-red-700 px-3 py-2 rounded-lg text-sm">{{ error }}</div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="transfers.length === 0" class="text-center text-gray-400 py-12 text-sm">Không có dữ liệu.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Ngày</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Từ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Đến</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Lý do</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="t in transfers" :key="t.name" class="hover:bg-gray-50 cursor-pointer" @click="router.push(`/asset-transfers/${t.name}`)">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ t.name }}</td>
            <td class="px-4 py-3 text-gray-600 whitespace-nowrap">{{ formatDate(t.transfer_date) }}</td>
            <td class="px-4 py-3 text-gray-800">{{ t.asset }}</td>
            <td class="px-4 py-3">
              <span :class="['text-xs px-2 py-1 rounded-full font-medium', TYPE_COLORS[t.transfer_type] || 'bg-gray-100 text-gray-600']">
                {{ t.transfer_type }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-500 text-xs">{{ t.from_location || '—' }}</td>
            <td class="px-4 py-3 text-gray-500 text-xs">{{ t.to_location }}</td>
            <td class="px-4 py-3 text-gray-500 max-w-xs truncate">{{ t.reason }}</td>
            <td class="px-4 py-3 text-right">
              <button @click="remove(t.name)" class="text-xs text-red-600 hover:text-red-800">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-sm text-gray-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button @click="prevPage" :disabled="page === 1" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50">‹</button>
          <button @click="nextPage" :disabled="page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50">›</button>
        </div>
      </div>
    </div>
  </div>
</template>
