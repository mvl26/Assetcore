<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'
import type { ServiceContract } from '@/types/imm00'

type ServiceContractRow = ServiceContract & { supplier_name?: string }

const router = useRouter()

const contracts = ref<ServiceContractRow[]>([])
const contractType = ref('')
const loading = ref(false)
const error = ref('')
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 30

const BASE = '/api/method/assetcore.api.imm00'

const CONTRACT_TYPES = ['Preventive Maintenance', 'Calibration', 'Repair', 'Full Service', 'Warranty Extension']

const CONTRACT_TYPE_LABEL: Record<string, string> = {
  'Preventive Maintenance': 'Bảo trì định kỳ',
  'Calibration': 'Hiệu chuẩn',
  'Repair': 'Sửa chữa',
  'Full Service': 'Trọn gói',
  'Warranty Extension': 'Gia hạn bảo hành',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await frappeGet<{ items: ServiceContractRow[]; pagination: { total: number } } | null>(
      `${BASE}.list_service_contracts`,
      {
        page: page.value,
        page_size: PAGE_SIZE,
        ...(contractType.value ? { contract_type: contractType.value } : {}),
      },
    )
    if (res) {
      contracts.value = res.items || []
      totalCount.value = res.pagination?.total || 0
    }
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không thể tải danh sách hợp đồng. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

function handleSearch() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; load() } }

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function daysUntilExpiry(d?: string) {
  if (!d) return null
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}

function expiryClass(d?: string) {
  const days = daysUntilExpiry(d)
  if (days === null) return 'text-gray-400'
  if (days < 30) return 'text-red-600 font-medium'
  if (days < 90) return 'text-yellow-600 font-medium'
  return 'text-gray-600'
}

const TYPE_COLORS: Record<string, string> = {
  'Preventive Maintenance': 'bg-blue-100 text-blue-700',
  'Calibration': 'bg-purple-100 text-purple-700',
  'Repair': 'bg-yellow-100 text-yellow-700',
  'Full Service': 'bg-green-100 text-green-700',
  'Warranty Extension': 'bg-gray-100 text-gray-600',
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Hợp đồng dịch vụ</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ totalCount }} hợp đồng</span>
        <button @click="router.push('/service-contracts/new')" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Tạo mới</button>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm flex items-center justify-between">
      <span>⚠ {{ error }}</span>
      <button class="text-xs underline text-red-700 hover:text-red-900" @click="load">Thử lại</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4 flex gap-3">
      <select
        v-model="contractType"
        class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        @change="handleSearch"
      >
        <option value="">Tất cả loại</option>
        <option v-for="t in CONTRACT_TYPES" :key="t" :value="t">{{ CONTRACT_TYPE_LABEL[t] || t }}</option>
      </select>
      <button @click="handleSearch" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Lọc</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="contracts.length === 0 && !error" class="text-center text-gray-400 py-12 text-sm">Chưa có hợp đồng dịch vụ nào.</div>
      <div v-else class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã HĐ</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên hợp đồng</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">NCC</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Bắt đầu</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hết hạn</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">SLA (giờ)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="c in contracts" :key="c.name" @click="router.push(`/service-contracts/${c.name}`)" class="hover:bg-gray-50 cursor-pointer">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ c.name }}</td>
            <td class="px-4 py-3 font-medium text-gray-800">{{ c.contract_title }}</td>
            <td class="px-4 py-3">
              <div class="text-gray-700">{{ c.supplier_name || c.supplier || '—' }}</div>
              <div v-if="c.supplier && c.supplier_name" class="text-xs text-gray-400 font-mono">{{ c.supplier }}</div>
            </td>
            <td class="px-4 py-3">
              <span :class="['text-xs px-2 py-1 rounded-full font-medium', TYPE_COLORS[c.contract_type] || 'bg-gray-100 text-gray-600']">
                {{ CONTRACT_TYPE_LABEL[c.contract_type] || c.contract_type }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-500">{{ formatDate(c.contract_start) }}</td>
            <td class="px-4 py-3" :class="expiryClass(c.contract_end)">{{ formatDate(c.contract_end) }}</td>
            <td class="px-4 py-3 text-gray-500">{{ c.sla_response_hours ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
      </div>
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
