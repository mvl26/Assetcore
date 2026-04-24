<script setup lang="ts">
import { ref, watch } from 'vue'
import SmartSelect from './SmartSelect.vue'
import type { MasterItem } from '@/stores/useMasterDataStore'

const props = defineProps<{
  show: boolean
  title?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  'confirm': [approver: string]
  'cancel': []
}>()

const selectedApprover = ref('')
const approverError = ref('')

watch(() => props.show, (v) => {
  if (v) {
    selectedApprover.value = ''
    approverError.value = ''
  }
})

function onApproverSelect(item: MasterItem) {
  selectedApprover.value = item.id
  approverError.value = ''
}

function handleConfirm() {
  if (!selectedApprover.value) {
    approverError.value = 'Vui lòng chọn người phê duyệt'
    return
  }
  emit('confirm', selectedApprover.value)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="$emit('cancel')" />
      <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6 animate-fade-in">
        <h3 class="text-base font-semibold text-slate-800 mb-1">
          {{ title ?? 'Gửi yêu cầu phê duyệt' }}
        </h3>
        <p class="text-sm text-slate-500 mb-5">
          Chọn người sẽ nhận email thông báo và phê duyệt tài liệu này.
        </p>

        <div class="form-group mb-5">
          <label class="form-label">Người phê duyệt <span class="text-red-500">*</span></label>
          <SmartSelect
            doctype="User"
            placeholder="Tìm tên hoặc email..."
            :model-value="selectedApprover"
            :has-error="!!approverError"
            @select="onApproverSelect"
          />
          <p v-if="approverError" class="mt-1 text-xs text-red-500">{{ approverError }}</p>
          <p class="mt-1 text-xs text-slate-400">Người được chọn sẽ nhận email với đường link trực tiếp đến tài liệu.</p>
        </div>

        <div class="flex justify-end gap-2.5">
          <button class="btn-ghost" :disabled="loading" @click="$emit('cancel')">Hủy</button>
          <button class="btn-primary" :disabled="loading" @click="handleConfirm">
            <span v-if="loading">Đang gửi...</span>
            <span v-else>Gửi yêu cầu phê duyệt</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
