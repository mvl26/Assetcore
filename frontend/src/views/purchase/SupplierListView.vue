<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listSuppliers, deleteSupplier } from '@/api/imm00'
import type { AcSupplier } from '@/types/imm00'

const router = useRouter()
const suppliers = ref<AcSupplier[]>([])
const search = ref('')
const loading = ref(false)
const error = ref('')
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 30

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listSuppliers(page.value, PAGE_SIZE, search.value) as unknown as { items: AcSupplier[]; pagination: { total: number } }
    suppliers.value = res?.items || []
    totalCount.value = res?.pagination?.total || 0
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi tải dữ liệu'
  } finally {
    loading.value = false
  }
}

function handleSearch() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; load() } }

async function remove(name: string) {
  if (!confirm(`Xóa nhà cung cấp "${name}"?`)) return
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
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Nhà cung cấp</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ totalCount }} nhà cung cấp</span>
        <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="router.push('/suppliers/new')">+ Thêm nhà cung cấp</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4 flex gap-3">
      <input
        v-model="search"
        type="text"
        placeholder="Tìm theo mã, tên, email, mã số thuế..."
        class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        @keyup.enter="handleSearch"
      />
      <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="handleSearch">Tìm</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="error" class="text-center text-red-500 py-12 text-sm">{{ error }}</div>
      <div v-else-if="suppliers.length === 0" class="text-center text-gray-400 py-12 text-sm">Không tìm thấy kết quả.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã nhà cung cấp</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên nhà cung cấp</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Quốc gia</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Email liên hệ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hết hạn HĐ</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="s in suppliers" :key="s.name" class="hover:bg-gray-50 cursor-pointer" @click="router.push(`/suppliers/${s.name}`)">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ s.name }}</td>
            <td class="px-4 py-3 font-medium text-gray-800">{{ s.supplier_name }}</td>
            <td class="px-4 py-3 text-gray-500 text-xs">{{ s.vendor_type || '—' }}</td>
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
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="router.push(`/suppliers/${s.name}`)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(s.name)">Xóa</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-sm text-gray-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50" @click="prevPage">‹</button>
          <button :disabled="page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50" @click="nextPage">›</button>
        </div>
      </div>
    </div>
  </div>
</template>
