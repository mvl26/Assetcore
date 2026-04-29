<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { frappeGet, frappePost } from '@/api/helpers'
import type { ImmCapaRecord } from '@/types/imm00'

const route = useRoute()
const router = useRouter()
const name = route.params.id as string

const capa = ref<ImmCapaRecord | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const closeForm = ref({ root_cause: '', corrective_action: '', preventive_action: '', effectiveness_check: '' })
const showCloseForm = ref(false)

const BASE = '/api/method/assetcore.api.imm00'

const statusColor: Record<string, string> = {
  Open: 'bg-blue-100 text-blue-700',
  'In Progress': 'bg-yellow-100 text-yellow-700',
  'Pending Verification': 'bg-purple-100 text-purple-700',
  Closed: 'bg-green-100 text-green-700',
  Overdue: 'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<string, string> = {
  Open: 'Đang mở',
  'In Progress': 'Đang xử lý',
  'Pending Verification': 'Chờ xác nhận',
  Closed: 'Đã đóng',
  Overdue: 'Quá hạn',
  Cancelled: 'Đã hủy',
}
const SEVERITY_LABELS: Record<string, string> = {
  Minor: 'Nhỏ',
  Major: 'Nghiêm trọng',
  Critical: 'Khẩn cấp',
}
function statusLabel(s?: string): string {
  return (s && STATUS_LABELS[s]) || s || ''
}
function severityLabel(s?: string): string {
  return (s && SEVERITY_LABELS[s]) || s || ''
}

const severityColor: Record<string, string> = {
  Minor: 'bg-gray-100 text-gray-600',
  Major: 'bg-orange-100 text-orange-700',
  Critical: 'bg-red-100 text-red-700',
}

const canClose = computed(() =>
  capa.value && !['Closed', 'Cancelled'].includes(capa.value.status)
)

async function load() {
  loading.value = true
  try {
    const res = await frappeGet<ImmCapaRecord>(`${BASE}.get_capa`, { name })
    capa.value = res
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không tải được CAPA'
  }
  loading.value = false
}

async function submitClose() {
  if (!closeForm.value.root_cause.trim() || !closeForm.value.corrective_action.trim() || !closeForm.value.preventive_action.trim()) {
    error.value = 'Vui lòng điền đủ Root Cause, Corrective Action, Preventive Action.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await frappePost<void>(`${BASE}.close_capa_record`, { name, ...closeForm.value })
    showCloseForm.value = false
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi đóng CAPA'
  }
  saving.value = false
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-6">
    <div class="flex items-center gap-3">
      <button class="text-gray-500 hover:text-gray-700 text-sm" @click="router.push('/capas')">← Quay lại</button>
      <h1 class="text-xl font-semibold text-gray-800">Chi tiết CAPA</h1>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>
    <div v-else-if="!capa" class="text-center text-red-500 py-12">{{ error || 'Không tìm thấy CAPA' }}</div>

    <template v-else>
      <!-- Header card -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs text-gray-400 font-mono">{{ capa.name }}</p>
            <p class="text-base font-medium text-gray-800 mt-1">{{ capa.description || '(Không có mô tả)' }}</p>
          </div>
          <div class="flex gap-2 flex-shrink-0">
            <span :class="['text-xs px-2 py-1 rounded-full font-medium', severityColor[capa.severity]]">{{ severityLabel(capa.severity) }}</span>
            <span :class="['text-xs px-2 py-1 rounded-full font-medium', statusColor[capa.status]]">{{ statusLabel(capa.status) }}</span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm pt-2 border-t border-gray-100">
          <div>
            <p class="text-gray-400 text-xs">Thiết bị</p>
            <p class="font-medium">{{ capa.asset_name || capa.asset || '—' }}</p>
            <p v-if="capa.asset_name" class="text-xs text-gray-400 font-mono">{{ capa.asset }}</p>
          </div>
          <div><p class="text-gray-400 text-xs">Hạn xử lý</p><p :class="['font-medium', capa.due_date && new Date(capa.due_date) < new Date() && capa.status !== 'Closed' ? 'text-red-600' : '']">{{ formatDate(capa.due_date) }}</p></div>
          <div><p class="text-gray-400 text-xs">Người phụ trách</p><p class="font-medium">{{ capa.owner || '—' }}</p></div>
          <div><p class="text-gray-400 text-xs">Ngày tạo</p><p class="font-medium">{{ formatDate(capa.creation) }}</p></div>
        </div>
      </div>

      <!-- Close CAPA -->
      <div v-if="canClose" class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="font-semibold text-gray-700">Đóng CAPA</h2>
          <button
            class="text-sm bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg"
            @click="showCloseForm = !showCloseForm"
          >
{{ showCloseForm ? 'Huỷ' : 'Đóng CAPA' }}
</button>
        </div>

        <div v-if="showCloseForm" class="space-y-3">
          <div v-if="error" class="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{{ error }}</div>
          <div>
            <label for="close-root-cause" class="block text-xs text-gray-500 mb-1">Root Cause <span class="text-red-500">*</span></label>
            <textarea id="close-root-cause" v-model="closeForm.root_cause" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400" placeholder="Nguyên nhân gốc rễ..."></textarea>
          </div>
          <div>
            <label for="close-corrective" class="block text-xs text-gray-500 mb-1">Corrective Action <span class="text-red-500">*</span></label>
            <textarea id="close-corrective" v-model="closeForm.corrective_action" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400" placeholder="Hành động khắc phục..."></textarea>
          </div>
          <div>
            <label for="close-preventive" class="block text-xs text-gray-500 mb-1">Preventive Action <span class="text-red-500">*</span></label>
            <textarea id="close-preventive" v-model="closeForm.preventive_action" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400" placeholder="Hành động phòng ngừa..."></textarea>
          </div>
          <div>
            <label for="close-effectiveness" class="block text-xs text-gray-500 mb-1">Effectiveness Check</label>
            <textarea id="close-effectiveness" v-model="closeForm.effectiveness_check" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400" placeholder="Xác minh hiệu quả (không bắt buộc)..."></textarea>
          </div>
          <button
            :disabled="saving"
            class="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white py-2 rounded-lg text-sm font-medium"
            @click="submitClose"
          >
{{ saving ? 'Đang lưu...' : 'Xác nhận đóng CAPA' }}
</button>
        </div>
      </div>

      <div v-if="capa.status === 'Closed'" class="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
        CAPA đã được đóng thành công.
      </div>
    </template>
  </div>
</template>
