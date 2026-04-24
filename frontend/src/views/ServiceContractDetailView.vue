<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { frappeGet, frappePost } from '@/api/helpers'
import type { ServiceContract } from '@/types/imm00'

const route = useRoute()
const router = useRouter()

const contract = ref<ServiceContract & { docstatus?: number } | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const BASE = '/api/method/assetcore.api.imm00'

async function load() {
  loading.value = true
  const name = route.params.id as string
  const res = await frappeGet<ServiceContract & { docstatus?: number } | null>(
    `${BASE}.get_service_contract`, { name },
  )
  contract.value = res
  loading.value = false
}

async function save() {
  if (!contract.value) return
  saving.value = true
  error.value = ''
  try {
    await frappePost<void>(`${BASE}.update_service_contract`, {
      name: contract.value.name,
      contract_title: contract.value.contract_title,
      contract_value: contract.value.contract_value,
      sla_response_hours: contract.value.sla_response_hours,
      coverage_description: contract.value.coverage_description,
    })
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lưu thất bại'
  }
  saving.value = false
}

async function submitContract() {
  if (!contract.value) return
  if (!confirm('Submit hợp đồng? Sau khi submit sẽ không thể sửa.')) return
  saving.value = true
  try {
    await frappePost<void>(`${BASE}.submit_service_contract`, { name: contract.value.name })
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Submit thất bại'
  }
  saving.value = false
}

async function remove() {
  if (!contract.value) return
  if (!confirm(`Xóa hợp đồng ${contract.value.name}?`)) return
  try {
    await frappePost<void>(`${BASE}.delete_service_contract`, { name: contract.value.name })
    router.push('/service-contracts')
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Xóa thất bại'
  }
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div class="flex items-center gap-3">
      <button @click="router.back()" class="text-gray-500 hover:text-gray-700 text-sm">← Quay lại</button>
      <h1 class="text-xl font-semibold text-gray-800">Chi tiết Hợp đồng dịch vụ</h1>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
    <div v-else-if="!contract" class="text-center text-gray-400 py-12">Không tìm thấy hợp đồng.</div>
    <div v-else class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">{{ error }}</div>

      <div class="flex items-center justify-between pb-4 border-b border-gray-100">
        <div>
          <p class="text-sm text-gray-500">Mã HĐ</p>
          <p class="font-mono text-sm font-medium">{{ contract.name }}</p>
        </div>
        <span :class="['text-xs px-3 py-1 rounded-full font-medium', contract.docstatus === 1 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700']">
          {{ contract.docstatus === 1 ? 'Đã gửi' : 'Nháp' }}
        </span>
      </div>

      <div>
        <label for="d-title" class="block text-sm font-medium text-gray-700 mb-1">Tên hợp đồng</label>
        <input id="d-title" v-model="contract.contract_title" :disabled="contract.docstatus === 1" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <p class="block text-sm font-medium text-gray-700 mb-1">Nhà cung cấp</p>
          <p class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">{{ contract.supplier }}</p>
        </div>
        <div>
          <p class="block text-sm font-medium text-gray-700 mb-1">Loại HĐ</p>
          <p class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">{{ contract.contract_type }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <p class="block text-sm font-medium text-gray-700 mb-1">Bắt đầu</p>
          <p class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">{{ formatDate(contract.contract_start) }}</p>
        </div>
        <div>
          <p class="block text-sm font-medium text-gray-700 mb-1">Kết thúc</p>
          <p class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">{{ formatDate(contract.contract_end) }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label for="d-value" class="block text-sm font-medium text-gray-700 mb-1">Giá trị HĐ</label>
          <input id="d-value" v-model.number="contract.contract_value" :disabled="contract.docstatus === 1" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
        </div>
        <div>
          <label for="d-sla" class="block text-sm font-medium text-gray-700 mb-1">SLA (giờ)</label>
          <input id="d-sla" v-model.number="contract.sla_response_hours" :disabled="contract.docstatus === 1" type="number" min="0" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
        </div>
      </div>

      <div>
        <label for="d-cov" class="block text-sm font-medium text-gray-700 mb-1">Phạm vi dịch vụ</label>
        <textarea id="d-cov" v-model="contract.coverage_description" :disabled="contract.docstatus === 1" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"></textarea>
      </div>

      <div class="flex gap-3 pt-4 border-t border-gray-100">
        <button v-if="contract.docstatus !== 1" @click="save" :disabled="saving" class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium">Lưu</button>
        <button v-if="contract.docstatus !== 1" @click="submitContract" :disabled="saving" class="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium">Gửi duyệt</button>
        <button @click="remove" class="ml-auto text-sm text-red-600 hover:text-red-800">Xóa</button>
      </div>
    </div>
  </div>
</template>
