<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { frappeGet, frappePost } from '@/api/helpers'
import type { ServiceContract } from '@/types/imm00'
import PageHeader from '@/components/common/PageHeader.vue'

const route = useRoute()
const router = useRouter()

const contract = ref<ServiceContract | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const editing = ref(false)

const BASE = '/api/method/assetcore.api.imm00'

const CONTRACT_TYPE_LABEL: Record<string, string> = {
  'Preventive Maintenance': 'Bảo trì định kỳ',
  Calibration: 'Hiệu chuẩn',
  Repair: 'Sửa chữa',
  'Full Service': 'Trọn gói',
  'Warranty Extension': 'Gia hạn bảo hành',
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const name = route.params.id as string
    const res = await frappeGet<ServiceContract | null>(`${BASE}.get_service_contract`, { name })
    contract.value = res
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không thể tải hợp đồng'
  } finally {
    loading.value = false
  }
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
      notes: contract.value.notes,
    })
    editing.value = false
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lưu thất bại'
  } finally { saving.value = false }
}

async function remove() {
  if (!contract.value) return
  if (!confirm(`Xóa hợp đồng ${contract.value.name}?`)) return
  try {
    await frappePost<void>(`${BASE}.delete_service_contract`, { name: contract.value.name })
    router.push('/service-contracts')
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Xóa thất bại — có thể đang được tham chiếu'
  }
}

function cancelEdit() {
  editing.value = false
  load() // discard local changes
}

function formatDate(d?: string) { return d ? new Date(d).toLocaleDateString('vi-VN') : '—' }
function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function daysUntilExpiry(d?: string) {
  if (!d) return null
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}
function expiryClass(d?: string) {
  const days = daysUntilExpiry(d)
  if (days === null) return 'text-slate-400'
  if (days < 0) return 'text-red-700 font-semibold'
  if (days < 30) return 'text-red-600 font-medium'
  if (days < 90) return 'text-yellow-600 font-medium'
  return 'text-slate-700'
}
function expiryStatusLabel(d?: string) {
  const days = daysUntilExpiry(d)
  if (days === null) return ''
  if (days < 0) return `Đã hết hạn ${Math.abs(days)} ngày`
  if (days < 30) return `Còn ${days} ngày — sắp hết hạn`
  if (days < 90) return `Còn ${days} ngày`
  return `Còn ${days} ngày`
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      back-to="/service-contracts"
      :title="contract?.contract_title || 'Chi tiết hợp đồng dịch vụ'"
      :subtitle="contract ? `Mã: ${contract.name}` : ''"
      :breadcrumb="[
        { label: 'Hợp đồng dịch vụ', to: '/service-contracts' },
        { label: contract?.name || 'Chi tiết' },
      ]"
    >
      <template #actions>
        <button
          v-if="contract && !editing"
          class="px-4 py-2 text-sm border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 font-medium"
          @click="editing = true"
        >Sửa</button>
        <button
          v-if="contract && !editing"
          class="px-4 py-2 text-sm border border-red-300 text-red-700 rounded-lg hover:bg-red-50 font-medium"
          @click="remove"
        >Xóa</button>
      </template>
    </PageHeader>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
    <div v-else-if="!contract" class="text-center text-gray-400 py-12">Không tìm thấy hợp đồng.</div>

    <template v-else>
      <div v-if="error" class="text-red-700 text-sm bg-red-50 px-3 py-2 rounded-lg border border-red-200">{{ error }}</div>

      <!-- Thông tin hợp đồng -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div class="flex items-start justify-between pb-4 border-b border-gray-100">
          <div>
            <p class="text-xs text-gray-500 uppercase tracking-wide">Mã hợp đồng</p>
            <p class="font-mono text-sm text-gray-700 mt-0.5">{{ contract.name }}</p>
          </div>
          <span
            v-if="contract.contract_end"
            class="text-xs px-3 py-1 rounded-full font-medium"
            :class="daysUntilExpiry(contract.contract_end)! < 0 ? 'bg-red-100 text-red-700' : daysUntilExpiry(contract.contract_end)! < 30 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'"
          >{{ expiryStatusLabel(contract.contract_end) }}</span>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Tên hợp đồng</label>
          <input
            v-if="editing"
            v-model="contract.contract_title"
            type="text"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <p v-else class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">{{ contract.contract_title }}</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p class="block text-sm font-medium text-gray-700 mb-1">Nhà cung cấp</p>
            <p class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">{{ contract.supplier }}</p>
          </div>
          <div>
            <p class="block text-sm font-medium text-gray-700 mb-1">Loại hợp đồng</p>
            <p class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">
              {{ CONTRACT_TYPE_LABEL[contract.contract_type] || contract.contract_type }}
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p class="block text-sm font-medium text-gray-700 mb-1">Bắt đầu</p>
            <p class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">{{ formatDate(contract.contract_start) }}</p>
          </div>
          <div>
            <p class="block text-sm font-medium text-gray-700 mb-1">Kết thúc</p>
            <p class="text-sm bg-gray-50 px-3 py-2 rounded-lg" :class="expiryClass(contract.contract_end)">
              {{ formatDate(contract.contract_end) }}
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Giá trị HĐ</label>
            <input
              v-if="editing"
              v-model.number="contract.contract_value"
              type="number" min="0"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <p v-else class="text-sm font-semibold text-emerald-700 bg-gray-50 px-3 py-2 rounded-lg">
              {{ vnd(contract.contract_value) }}
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">SLA phản hồi (giờ)</label>
            <input
              v-if="editing"
              v-model.number="contract.sla_response_hours"
              type="number" min="0"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <p v-else class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg">
              {{ contract.sla_response_hours ?? '—' }}
            </p>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Phạm vi dịch vụ</label>
          <textarea
            v-if="editing"
            v-model="contract.coverage_description"
            rows="3"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          ></textarea>
          <p v-else class="text-sm text-gray-800 bg-gray-50 px-3 py-2 rounded-lg whitespace-pre-line min-h-[40px]">
            {{ contract.coverage_description || '—' }}
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
          <textarea
            v-if="editing"
            v-model="contract.notes"
            rows="2"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          ></textarea>
          <p v-else class="text-sm text-gray-700 bg-gray-50 px-3 py-2 rounded-lg whitespace-pre-line min-h-[40px]">
            {{ contract.notes || '—' }}
          </p>
        </div>

        <!-- Edit mode: Lưu / Hủy -->
        <div v-if="editing" class="flex gap-3 pt-4 border-t border-gray-100">
          <button
            :disabled="saving"
            class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
            @click="save"
          >{{ saving ? 'Đang lưu...' : 'Lưu thay đổi' }}</button>
          <button
            :disabled="saving"
            class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            @click="cancelEdit"
          >Hủy</button>
        </div>
      </div>
    </template>
  </div>
</template>
