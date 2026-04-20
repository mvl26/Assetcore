<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTransferFull, updateTransfer, approveTransfer } from '@/api/imm00'
import { frappePost } from '@/api/helpers'

const route = useRoute()
const router = useRouter()
const name = computed(() => route.params.id as string)

const form = ref<Record<string, string | number | null | undefined>>({})
const loading = ref(false)
const saving = ref(false)
const err = ref('')
const isLocked = computed(() => !!form.value.approved_by)

async function load() {
  loading.value = true
  try {
    const r = await getTransferFull(name.value) as unknown as Record<string, string | number | null> | null
    if (r) form.value = { ...r }
  } finally { loading.value = false }
}

async function save() {
  saving.value = true; err.value = ''
  try { await updateTransfer(name.value, form.value as Record<string, unknown>); await load() }
  catch (e: unknown) { err.value = (e as Error).message || 'Lỗi lưu' }
  finally { saving.value = false }
}

async function approve() {
  if (!confirm('Phê duyệt Transfer này? Sau phê duyệt sẽ khóa chỉnh sửa.')) return
  try { await approveTransfer(name.value); await load() }
  catch (e: unknown) { err.value = (e as Error).message || 'Lỗi phê duyệt' }
}

async function remove() {
  if (!confirm(`Xóa Transfer "${name.value}"?`)) return
  try {
    await frappePost('/api/method/assetcore.api.imm00.delete_transfer', { name: name.value })
    router.push('/asset-transfers')
  } catch (e: unknown) { err.value = (e as Error).message || 'Không thể xóa' }
}

onMounted(load)
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto space-y-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-800">Chuyển giao — {{ name }}</h1>
        <p class="text-xs text-gray-500 mt-1">
          {{ form.transfer_type }} · {{ form.transfer_date }}
          <span v-if="isLocked" class="ml-2 text-green-600 font-semibold">✓ Đã phê duyệt bởi {{ form.approved_by }}</span>
        </p>
      </div>
      <div class="flex gap-2">
        <button v-if="!isLocked" @click="approve" class="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium">Phê duyệt</button>
        <button v-if="!isLocked" @click="remove" class="text-red-600 text-sm font-medium">Xóa</button>
      </div>
    </div>

    <div v-if="err" class="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{{ err }}</div>
    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>

    <div v-else class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Thiết bị (AC Asset)</label>
          <input v-model="form.asset" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Loại chuyển giao</label>
          <select v-model="form.transfer_type" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50">
            <option>Internal</option><option>Loan</option><option>External</option><option>Return</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Ngày chuyển</label>
          <input v-model="form.transfer_date" type="date" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Ngày dự kiến trả (nếu loan)</label>
          <input v-model="form.expected_return_date" type="date" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-6 border-t pt-4">
        <div class="space-y-3">
          <h3 class="font-semibold text-sm text-gray-700">Từ (From)</h3>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Vị trí</label>
            <input v-model="form.from_location" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Khoa/Phòng</label>
            <input v-model="form.from_department" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Người giao</label>
            <input v-model="form.from_custodian" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>
        </div>
        <div class="space-y-3">
          <h3 class="font-semibold text-sm text-gray-700">Đến (To)</h3>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Vị trí *</label>
            <input v-model="form.to_location" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Khoa/Phòng</label>
            <input v-model="form.to_department" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Người nhận</label>
            <input v-model="form.to_custodian" :disabled="isLocked" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>
        </div>
      </div>

      <div class="border-t pt-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">Lý do chuyển *</label>
        <textarea v-model="form.reason" :disabled="isLocked" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"></textarea>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Ghi chú</label>
        <textarea v-model="form.notes" :disabled="isLocked" rows="2" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50"></textarea>
      </div>

      <div v-if="!isLocked" class="flex justify-end gap-2 pt-4 border-t border-gray-100">
        <button @click="router.push('/asset-transfers')" class="px-4 py-2 text-sm border border-gray-300 rounded-lg">Quay lại</button>
        <button @click="save" :disabled="saving" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50">
          {{ saving ? 'Đang lưu...' : 'Lưu' }}
        </button>
      </div>
    </div>
  </div>
</template>
