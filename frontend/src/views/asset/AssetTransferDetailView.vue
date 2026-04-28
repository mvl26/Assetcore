<script setup lang="ts">
import DateInput from '@/components/common/DateInput.vue'
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTransferFull, updateTransfer, approveTransfer } from '@/api/imm00'
import { frappePost } from '@/api/helpers'

const route  = useRoute()
const router = useRouter()
const name   = computed(() => route.params.id as string)

const form    = ref<Record<string, string | number | null | undefined>>({})
const loading = ref(false)
const saving  = ref(false)
const err     = ref('')
const rejectionReason = ref('')
const handoverNotes   = ref('')
const showRejectModal = ref(false)

const status    = computed(() => (form.value.status as string) || '')
const isPending  = computed(() => status.value === 'Pending Approval' || !status.value)
const isApproved = computed(() => status.value === 'Approved')
const isEditable = computed(() => isPending.value)

const STATUS_COLOR: Record<string, string> = {
  'Pending Approval': 'bg-yellow-100 text-yellow-700',
  'Approved':         'bg-green-100 text-green-700',
  'Rejected':         'bg-red-100 text-red-700',
  'Received':         'bg-blue-100 text-blue-700',
  'Cancelled':        'bg-gray-100 text-gray-500',
}
const STATUS_LABEL: Record<string, string> = {
  'Pending Approval': 'Chờ phê duyệt',
  'Approved':         'Đã phê duyệt',
  'Rejected':         'Từ chối',
  'Received':         'Đã tiếp nhận',
  'Cancelled':        'Đã hủy',
}

async function load() {
  loading.value = true
  try {
    const r = await getTransferFull(name.value) as unknown as Record<string, string | number | null> | null
    if (r) form.value = { ...r }
  } finally { loading.value = false }
}

async function save() {
  saving.value = true; err.value = ''
  try {
    await updateTransfer(name.value, {
      to_location: form.value.to_location,
      to_department: form.value.to_department,
      to_custodian: form.value.to_custodian,
      reason: form.value.reason,
      notes: form.value.notes,
      expected_return_date: form.value.expected_return_date,
    })
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
  finally { saving.value = false }
}

async function approve() {
  if (!confirm('Phê duyệt phiếu luân chuyển này? Vị trí thiết bị sẽ được cập nhật ngay.')) return
  err.value = ''
  try { await approveTransfer(name.value); await load() }
  catch (e: unknown) { err.value = (e as Error).message || 'Lỗi phê duyệt' }
}

async function reject() {
  if (!rejectionReason.value || rejectionReason.value.trim().length < 5) {
    err.value = 'Lý do từ chối tối thiểu 5 ký tự'
    return
  }
  err.value = ''
  try {
    await frappePost('/api/method/assetcore.api.imm00.reject_transfer', {
      name: name.value,
      rejection_reason: rejectionReason.value,
    })
    showRejectModal.value = false
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi từ chối' }
}

async function confirmReceipt() {
  if (!confirm('Xác nhận đã tiếp nhận thiết bị tại vị trí mới?')) return
  err.value = ''
  try {
    await frappePost('/api/method/assetcore.api.imm00.receive_transfer', {
      name: name.value,
      handover_notes: handoverNotes.value,
    })
    await load()
  } catch (e: unknown) { err.value = (e as Error).message || 'Lỗi xác nhận tiếp nhận' }
}

async function cancel() {
  if (!confirm(`Hủy phiếu "${name.value}"?`)) return
  err.value = ''
  try {
    await frappePost('/api/method/assetcore.api.imm00.delete_transfer', { name: name.value })
    router.push('/asset-transfers')
  } catch (e: unknown) { err.value = (e as Error).message || 'Không thể hủy' }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
<!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Phiếu Luân chuyển</p>
        <h1 class="text-xl font-semibold text-gray-800">{{ name }}</h1>
        <p class="text-xs text-gray-500 mt-1">{{ form.transfer_type }} · {{ form.transfer_date }}</p>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="status" class="text-xs font-semibold px-2.5 py-1 rounded-full" :class="STATUS_COLOR[status]">
          {{ STATUS_LABEL[status] || status }}
        </span>
        <!-- Action buttons -->
        <template v-if="isPending">
          <button class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors" @click="approve">
            Phê duyệt
          </button>
          <button class="bg-red-50 hover:bg-red-100 text-red-600 px-4 py-2 rounded-lg text-sm font-medium transition-colors" @click="showRejectModal = true">
            Từ chối
          </button>
          <button class="text-gray-400 hover:text-gray-600 text-sm" @click="cancel">Hủy phiếu</button>
        </template>
        <template v-if="isApproved">
          <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors" @click="confirmReceipt">
            Xác nhận tiếp nhận
          </button>
        </template>
      </div>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>
    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>

    <div v-else class="space-y-4">
<!-- Main form -->
      <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị</label>
            <input v-model="form.asset" disabled class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Loại chuyển giao</label>
            <select v-model="form.transfer_type" :disabled="!isEditable" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50">
              <option>Internal</option><option>Loan</option><option>External</option><option>Return</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ngày yêu cầu</label>
            <DateInput v-model="form.transfer_date" disabled class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50" />
          </div>
          <div v-if="form.transfer_type === 'Loan'">
            <label class="block text-sm font-medium text-gray-700 mb-1">Ngày trả dự kiến</label>
            <DateInput v-model="form.expected_return_date" :disabled="!isEditable" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>
        </div>

        <!-- From / To -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 border-t pt-4">
          <div class="space-y-3">
            <h3 class="font-semibold text-sm text-gray-700">Từ (nguồn)</h3>
            <div>
              <label for="from_location" class="block text-xs font-medium text-gray-500 mb-1">Vị trí hiện tại</label>
              <input id="from_location" v-model="form.from_location" disabled class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50" />
            </div>
            <div>
              <label for="from_department" class="block text-xs font-medium text-gray-500 mb-1">Phòng ban</label>
              <input id="from_department" v-model="form.from_department" disabled class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50" />
            </div>
            <div>
              <label for="from_custodian" class="block text-xs font-medium text-gray-500 mb-1">Phụ trách</label>
              <input id="from_custodian" v-model="form.from_custodian" disabled class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50" />
            </div>
          </div>
          <div class="space-y-3">
            <h3 class="font-semibold text-sm text-gray-700">Đến (đích) <span class="text-red-500">*</span></h3>
            <div>
              <label for="to_location" class="block text-xs font-medium text-gray-500 mb-1">Vị trí mới</label>
              <input id="to_location" v-model="form.to_location" :disabled="!isEditable" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
            </div>
            <div>
              <label for="to_department" class="block text-xs font-medium text-gray-500 mb-1">Phòng ban</label>
              <input id="to_department" v-model="form.to_department" :disabled="!isEditable" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
            </div>
            <div>
              <label for="to_custodian" class="block text-xs font-medium text-gray-500 mb-1">Người nhận</label>
              <input id="to_custodian" v-model="form.to_custodian" :disabled="!isEditable" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
            </div>
          </div>
        </div>

        <div class="border-t pt-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Lý do chuyển <span class="text-red-500">*</span></label>
          <textarea v-model="form.reason" :disabled="!isEditable" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
          <textarea v-model="form.notes" :disabled="!isEditable" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
        </div>

        <div v-if="isEditable" class="flex justify-end gap-2 pt-2 border-t border-gray-100">
          <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50" @click="router.push('/asset-transfers')">Quay lại</button>
          <button :disabled="saving" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50 hover:bg-blue-700" @click="save">
            {{ saving ? 'Đang lưu...' : 'Lưu thay đổi' }}
          </button>
        </div>
      </div>

      <!-- Approval info -->
      <div v-if="form.approved_by || form.rejected_by || form.received_by" class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h3 class="text-sm font-semibold text-gray-700">Thông tin xử lý</h3>
        <div v-if="form.approved_by" class="flex gap-6 text-sm">
          <div><span class="text-gray-500">Người phê duyệt:</span> <span class="font-medium text-green-700">{{ form.approved_by }}</span></div>
          <div><span class="text-gray-500">Ngày:</span> {{ form.approval_date }}</div>
        </div>
        <div v-if="form.rejected_by" class="space-y-1 text-sm">
          <div class="flex gap-6">
            <div><span class="text-gray-500">Người từ chối:</span> <span class="font-medium text-red-600">{{ form.rejected_by }}</span></div>
          </div>
          <div class="bg-red-50 rounded-lg p-3 text-red-700">{{ form.rejection_reason }}</div>
        </div>
        <div v-if="form.received_by" class="flex gap-6 text-sm">
          <div><span class="text-gray-500">Người tiếp nhận:</span> <span class="font-medium text-blue-700">{{ form.received_by }}</span></div>
          <div><span class="text-gray-500">Ngày:</span> {{ form.received_date }}</div>
        </div>
        <div v-if="form.handover_notes" class="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{{ form.handover_notes }}</div>
      </div>

      <!-- Handover notes input when Approved -->
      <div v-if="isApproved" class="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p class="text-sm font-medium text-blue-800 mb-2">Ghi chú bàn giao (tùy chọn)</p>
        <textarea v-model="handoverNotes" rows="2" placeholder="Tình trạng thiết bị khi bàn giao..." class="w-full border border-blue-200 rounded-lg px-3 py-2 text-sm bg-white" />
      </div>
    </div>

    <!-- Reject modal -->
    <Teleport to="body">
      <div v-if="showRejectModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div class="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md mx-4">
          <h3 class="text-base font-semibold text-gray-800 mb-4">Từ chối phiếu luân chuyển</h3>
          <label for="rejection_reason" class="block text-sm font-medium text-gray-700 mb-1">Lý do từ chối <span class="text-red-500">*</span></label>
          <textarea id="rejection_reason" v-model="rejectionReason" rows="3" placeholder="Nêu rõ lý do (tối thiểu 5 ký tự)..." class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4" />
          <div class="flex justify-end gap-2">
            <button class="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50" @click="showRejectModal = false; rejectionReason = ''">Hủy</button>
            <button class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700" @click="reject">Xác nhận từ chối</button>
          </div>
        </div>
      </div>
    </Teleport>
</div>
</template>
