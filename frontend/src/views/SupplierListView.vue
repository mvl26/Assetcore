<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'
import { deleteSupplier } from '@/api/imm00'
import type { AcSupplier } from '@/types/imm00'

const router = useRouter()
const suppliers = ref<AcSupplier[]>([])
const search = ref('')
const loading = ref(false)
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 30

const BASE = '/api/method/assetcore.api.imm00'

async function load() {
  loading.value = true
  const res = await frappeGet<{ items: AcSupplier[]; pagination: { total: number } } | null>(
    `${BASE}.list_suppliers`,
    { page: page.value, page_size: PAGE_SIZE, search: search.value },
  )
  loading.value = false
  if (res) {
    suppliers.value = res.items || []
    totalCount.value = res.pagination?.total || 0
  }
}

function handleSearch() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; load() } }

async function remove(name: string) {
  if (!confirm(`Xóa NCC "${name}"?`)) return
  try { await deleteSupplier(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu') }
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('vi-VN')
}

function daysUntilExpiry(d: string) {
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Nhà cung cấp</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ totalCount }} NCC</span>
        <button @click="router.push('/suppliers/new')" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Thêm NCC</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4 flex gap-3">
      <input
        v-model="search"
        type="text"
        placeholder="Tìm kiếm nhà cung cấp..."
        class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        @keyup.enter="handleSearch"
      />
      <button @click="handleSearch" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Tìm</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="suppliers.length === 0" class="text-center text-gray-400 py-12 text-sm">Không có dữ liệu.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã NCC</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên NCC</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Quốc gia</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Email liên hệ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hết hạn HĐ</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="s in suppliers" :key="s.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ s.name }}</td>
            <td class="px-4 py-3 font-medium text-gray-800">{{ s.supplier_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ s.supplier_group || '—' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ s.country || '—' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ s.email_id || '—' }}</td>
            <td class="px-4 py-3">
              <template v-if="s.contract_end">
                <span :class="['text-xs font-medium', daysUntilExpiry(s.contract_end) < 30 ? 'text-red-600' : daysUntilExpiry(s.contract_end) < 90 ? 'text-yellow-600' : 'text-gray-600']">
                  {{ formatDate(s.contract_end) }}
                </span>
              </template>
              <span v-else class="text-gray-400">—</span>
            </td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button @click="router.push(`/suppliers/${s.name}`)" class="text-blue-600 hover:text-blue-800 text-xs font-medium">Sửa</button>
              <button @click="remove(s.name)" class="text-red-600 hover:text-red-800 text-xs font-medium">Xóa</button>
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
