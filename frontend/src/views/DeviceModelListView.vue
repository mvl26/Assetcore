<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'
import { deleteDeviceModel } from '@/api/imm00'
import type { ImmDeviceModel } from '@/types/imm00'

const router = useRouter()
const models = ref<ImmDeviceModel[]>([])
const search = ref('')
const loading = ref(false)
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 30

const BASE = '/api/method/assetcore.api.imm00'

const CLASS_COLOR: Record<string, string> = {
  'Class I':   'bg-green-100 text-green-700',
  'Class II':  'bg-yellow-100 text-yellow-700',
  'Class III': 'bg-red-100 text-red-700',
}

async function load() {
  loading.value = true
  const res = await frappeGet<{ items: ImmDeviceModel[]; pagination: { total: number } } | null>(
    `${BASE}.list_device_models`,
    { page: page.value, page_size: PAGE_SIZE, search: search.value },
  )
  loading.value = false
  if (res) {
    models.value = res.items || []
    totalCount.value = res.pagination?.total || 0
  }
}

function handleSearch() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; load() } }

async function remove(name: string) {
  if (!confirm(`Xóa Model "${name}"?`)) return
  try { await deleteDeviceModel(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu') }
}

onMounted(load)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Device Models</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ totalCount }} models</span>
        <button @click="router.push('/device-models/new')" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Thêm Model</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4 flex gap-3">
      <input
        v-model="search"
        type="text"
        placeholder="Tìm model, nhà sản xuất, mã model..."
        class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        @keyup.enter="handleSearch"
      />
      <button @click="handleSearch" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Tìm</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="models.length === 0" class="text-center text-gray-400 py-12 text-sm">Không có dữ liệu.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên model</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Nhà sản xuất</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Model number</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phân loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">GMDN</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="m in models" :key="m.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ m.name }}</td>
            <td class="px-4 py-3 font-medium text-gray-800">{{ m.model_name }}</td>
            <td class="px-4 py-3 text-gray-600">{{ m.manufacturer || '—' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ m.model_number || '—' }}</td>
            <td class="px-4 py-3">
              <span v-if="m.medical_device_class" :class="['text-xs px-2 py-1 rounded-full font-medium', CLASS_COLOR[m.medical_device_class] || 'bg-gray-100 text-gray-600']">
                {{ m.medical_device_class }}
              </span>
              <span v-else class="text-gray-400">—</span>
            </td>
            <td class="px-4 py-3 text-gray-500 font-mono text-xs">{{ m.gmdn_code || '—' }}</td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button @click="router.push(`/device-models/${m.name}`)" class="text-blue-600 hover:text-blue-800 text-xs font-medium">Sửa</button>
              <button @click="remove(m.name)" class="text-red-600 hover:text-red-800 text-xs font-medium">Xóa</button>
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
