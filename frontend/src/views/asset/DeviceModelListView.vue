<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listDeviceModels, deleteDeviceModel } from '@/api/imm00'
import type { ImmDeviceModel } from '@/types/imm00'

const router = useRouter()
const models = ref<ImmDeviceModel[]>([])
const search = ref('')
const loading = ref(false)
const error = ref('')
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 30

// Lightbox preview ảnh model
const previewUrl = ref('')
const previewName = ref('')
function openPreview(url: string, label: string, e: Event) {
  e.stopPropagation()
  previewUrl.value = url
  previewName.value = label
}
function closePreview() { previewUrl.value = ''; previewName.value = '' }
function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  img.dataset.failed = '1'
}

const CLASS_COLOR: Record<string, string> = {
  'Class I':   'bg-green-100 text-green-700',
  'Class II':  'bg-yellow-100 text-yellow-700',
  'Class III': 'bg-red-100 text-red-700',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listDeviceModels(page.value, PAGE_SIZE, search.value) as unknown as { items: ImmDeviceModel[]; pagination: { total: number } }
    models.value = res?.items || []
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
  if (!confirm(`Xóa Model thiết bị "${name}"?`)) return
  try { await deleteDeviceModel(name); await load() }
  catch (e: unknown) { alert((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu') }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-gray-800">Model thiết bị</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ totalCount }} model thiết bị</span>
        <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="router.push('/device-models/new')">+ Thêm Model thiết bị</button>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4 flex gap-3">
      <input
        v-model="search"
        type="text"
        placeholder="Tìm theo mã, tên model, hãng sản xuất, phiên bản, GMDN..."
        class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        @keyup.enter="handleSearch"
      />
      <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="handleSearch">Tìm</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="error" class="text-center text-red-500 py-12 text-sm">{{ error }}</div>
      <div v-else-if="models.length === 0" class="text-center text-gray-400 py-12 text-sm">Không tìm thấy kết quả.</div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 w-12"></th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Mã</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tên model</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Nhà sản xuất</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phiên bản</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Phân loại</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">GMDN</th>
            <th class="px-4 py-3 text-right"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="m in models" :key="m.name" class="hover:bg-gray-50 cursor-pointer" @click="router.push(`/device-models/${m.name}`)">
            <td class="px-4 py-3">
              <button
v-if="m.model_image" type="button"
                      class="block w-12 h-12 rounded-lg border border-slate-200 bg-slate-50 overflow-hidden hover:ring-2 hover:ring-blue-400 transition"
                      :title="`Xem ảnh — ${m.model_name}`"
                      @click="openPreview(m.model_image as string, m.model_name || m.name, $event)">
                <img
:src="m.model_image" alt="" loading="lazy" class="w-full h-full object-cover data-[failed=1]:hidden"
                     @error="onImgError" />
              </button>
              <div v-else class="w-12 h-12 rounded-lg border border-dashed border-slate-200 bg-slate-50/60 flex items-center justify-center text-slate-300">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-xs text-gray-500">{{ m.name }}</td>
            <td class="px-4 py-3 font-medium text-gray-800">
              {{ m.model_name }}
              <p v-if="m.asset_category" class="text-[10px] text-slate-400 font-normal mt-0.5">{{ m.asset_category }}</p>
            </td>
            <td class="px-4 py-3 text-gray-600">{{ m.manufacturer || '—' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ m.model_version || '—' }}</td>
            <td class="px-4 py-3">
              <span v-if="m.medical_device_class" :class="['text-xs px-2 py-1 rounded-full font-medium', CLASS_COLOR[m.medical_device_class] || 'bg-gray-100 text-gray-600']">
                {{ m.medical_device_class }}
              </span>
              <span v-else class="text-gray-400">—</span>
            </td>
            <td class="px-4 py-3 text-gray-500 font-mono text-xs">{{ m.gmdn_code || '—' }}</td>
            <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
              <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click="router.push(`/device-models/${m.name}`)">Sửa</button>
              <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="remove(m.name)">Xóa</button>
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

    <!-- Lightbox preview ảnh model -->
    <div
v-if="previewUrl"
         class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6 cursor-zoom-out"
         @click="closePreview"
         @keydown.esc="closePreview">
      <div class="relative max-w-5xl max-h-[90vh] flex flex-col items-center" @click.stop>
        <img
:src="previewUrl" :alt="previewName"
             class="max-w-full max-h-[80vh] object-contain rounded-lg shadow-2xl bg-white" />
        <div class="mt-3 flex items-center gap-3 text-white text-sm">
          <span class="font-medium">{{ previewName }}</span>
          <a
:href="previewUrl" target="_blank" rel="noopener"
             class="text-blue-200 hover:text-white underline-offset-4 hover:underline">
            Mở tab mới
          </a>
          <button
type="button"
                  class="ml-2 px-3 py-1 rounded-md bg-white/10 hover:bg-white/20 border border-white/20"
                  @click="closePreview">
Đóng (Esc)
</button>
        </div>
      </div>
    </div>
  </div>
</template>
