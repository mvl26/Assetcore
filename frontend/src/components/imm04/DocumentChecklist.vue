<script setup lang="ts">
import { computed } from 'vue'
import type { DocumentRecord } from '@/types/imm04'

const props = defineProps<{
  documents: DocumentRecord[]
  readonly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update', idx: number, field: keyof DocumentRecord, value: string): void
}>()

const receivedCount = computed(() => props.documents.filter((d) => d.status === 'Received').length)
const totalCount = computed(() => props.documents.length)
const completionPct = computed(() =>
  totalCount.value ? Math.round((receivedCount.value / totalCount.value) * 100) : 0,
)

function onToggleStatus(idx: number, currentStatus: string) {
  if (!props.readonly) {
    const newStatus = currentStatus === 'Received' ? 'Pending' : 'Received'
    emit('update', idx, 'status', newStatus)
  }
}

function onRemarksChange(idx: number, value: string) {
  if (!props.readonly) {
    emit('update', idx, 'remarks', value)
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- Progress -->
    <div class="flex items-center gap-3">
      <div class="flex-1 bg-gray-200 rounded-full h-2">
        <div
          class="h-2 rounded-full transition-all duration-300"
          :class="completionPct === 100 ? 'bg-green-500' : 'bg-blue-500'"
          :style="{ width: `${completionPct}%` }"
        />
      </div>
      <span class="text-sm text-gray-600 font-medium whitespace-nowrap">
        {{ receivedCount }} / {{ totalCount }} tài liệu
      </span>
    </div>

    <!-- Empty state -->
    <div v-if="!documents.length" class="text-center py-8 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
      <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="text-sm">Chưa có hồ sơ đi kèm</p>
    </div>

    <!-- Document list -->
    <div v-else class="space-y-2">
      <div
        v-for="doc in documents"
        :key="doc.idx"
        class="flex items-start gap-3 p-3 rounded-lg border transition-colors"
        :class="doc.status === 'Received' ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'"
      >
        <!-- Checkbox -->
        <button
          :disabled="readonly"
          class="mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors"
          :class="[
            doc.status === 'Received'
              ? 'bg-green-500 border-green-500 text-white'
              : 'border-gray-300 hover:border-blue-400',
            readonly ? 'cursor-default' : 'cursor-pointer',
          ]"
          @click="onToggleStatus(doc.idx, doc.status)"
        >
          <svg v-if="doc.status === 'Received'" class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
          </svg>
        </button>

        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-2">
            <div>
              <p class="text-sm font-medium text-gray-900">{{ doc.doc_type }}</p>
              <p v-if="doc.received_date" class="text-xs text-gray-500 mt-0.5">
                Ngày nhận: {{ doc.received_date }}
              </p>
            </div>
            <span
              class="text-xs px-2 py-0.5 rounded-full flex-shrink-0"
              :class="doc.status === 'Received' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
            >
              {{ doc.status === 'Received' ? 'Đã nhận' : 'Chưa nhận' }}
            </span>
          </div>

          <!-- Remarks -->
          <div v-if="!readonly || doc.remarks" class="mt-2">
            <input
              v-if="!readonly"
              type="text"
              :value="doc.remarks"
              class="form-input text-xs"
              placeholder="Ghi chú (tùy chọn)..."
              @change="onRemarksChange(doc.idx, ($event.target as HTMLInputElement).value)"
            />
            <p v-else-if="doc.remarks" class="text-xs text-gray-500 italic">{{ doc.remarks }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
