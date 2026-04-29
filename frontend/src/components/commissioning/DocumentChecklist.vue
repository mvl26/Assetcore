<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DocumentRecord } from '@/types/imm04'

const props = defineProps<{
  documents: DocumentRecord[]
  readonly?: boolean
  /** Phiếu này đã được mark "thiếu hồ sơ" — UI hiển thị banner cảnh báo */
  incompleteFlag?: 0 | 1
}>()

const emit = defineEmits<{
  /** Cập nhật 1 field của 1 row */
  (e: 'update', idx: number, field: keyof DocumentRecord, value: string | number): void
  /** Thêm row mới vào cuối — caller tự gán idx */
  (e: 'add'): void
  /** Xóa row theo idx */
  (e: 'remove', idx: number): void
}>()

const DOC_TYPE_OPTIONS = [
  'CO - Chứng nhận Xuất xứ',
  'CQ - Chứng nhận Chất lượng',
  'Packing List',
  'Manual / HDSD',
  'Warranty Card',
  'Training Certificate',
  'Other',
]

const STATUS_OPTIONS: { value: string; label: string; class: string }[] = [
  { value: 'Pending',  label: 'Chưa nhận',  class: 'bg-yellow-100 text-yellow-700' },
  { value: 'Received', label: 'Đã nhận',    class: 'bg-green-100 text-green-700' },
  { value: 'Missing',  label: 'Thiếu',      class: 'bg-red-100 text-red-700' },
  { value: 'Rejected', label: 'Không hợp lệ', class: 'bg-red-100 text-red-700' },
  { value: 'Waived',   label: 'Miễn',       class: 'bg-slate-100 text-slate-600' },
]
const STATUS_CLASS: Record<string, string> = Object.fromEntries(
  STATUS_OPTIONS.map(s => [s.value, s.class]),
)

// Stats
const receivedCount = computed(() => props.documents.filter(d => d.status === 'Received' || d.status === 'Waived').length)
const totalCount = computed(() => props.documents.length)
const completionPct = computed(() =>
  totalCount.value ? Math.round((receivedCount.value / totalCount.value) * 100) : 0,
)
const missingMandatory = computed(() =>
  props.documents.filter(d => d.is_mandatory && !['Received', 'Waived'].includes(d.status))
    .map(d => d.doc_type),
)

// Row expansion (chi tiết / số tài liệu / file / hết hạn)
const expanded = ref<Set<number>>(new Set())
function toggleExpand(idx: number) {
  if (expanded.value.has(idx)) expanded.value.delete(idx)
  else expanded.value.add(idx)
}

function updateField(idx: number, field: keyof DocumentRecord, value: string | number) {
  if (props.readonly) return
  emit('update', idx, field, value)
}

function daysUntilExpiry(d?: string): number | null {
  if (!d) return null
  const now = new Date(); now.setHours(0, 0, 0, 0)
  const exp = new Date(d); exp.setHours(0, 0, 0, 0)
  return Math.floor((exp.getTime() - now.getTime()) / 86400000)
}
function expiryClass(d?: string): string {
  const days = daysUntilExpiry(d)
  if (days === null) return ''
  if (days <= 0) return 'text-red-600 font-semibold'
  if (days <= 30) return 'text-orange-600'
  if (days <= 90) return 'text-yellow-600'
  return 'text-slate-500'
}
function expiryLabel(d?: string): string {
  const days = daysUntilExpiry(d)
  if (days === null) return ''
  if (days <= 0) return `Đã hết hạn (${d})`
  if (days <= 30) return `Còn ${days} ngày`
  return `HH: ${d}`
}
</script>

<template>
  <div class="space-y-3">
    <!-- Progress + add button -->
    <div class="flex items-center gap-3">
      <div class="flex-1 bg-slate-200 rounded-full h-2">
        <div
          class="h-2 rounded-full transition-all duration-300"
          :class="completionPct === 100 ? 'bg-green-500' : 'bg-blue-500'"
          :style="{ width: `${completionPct}%` }"
        />
      </div>
      <span class="text-sm text-slate-600 font-medium whitespace-nowrap">
        {{ receivedCount }} / {{ totalCount }} tài liệu
      </span>
      <button
        v-if="!readonly"
        type="button"
        class="text-xs px-3 py-1.5 rounded-lg border border-blue-300 text-blue-700 hover:bg-blue-50 font-medium whitespace-nowrap"
        @click="emit('add')"
      >+ Thêm hồ sơ</button>
    </div>

    <!-- Banner cảnh báo nếu thiếu mandatory -->
    <div
      v-if="missingMandatory.length"
      :class="[
        'rounded-lg px-3 py-2 text-sm flex items-start gap-2',
        incompleteFlag
          ? 'bg-orange-50 border border-orange-200 text-orange-800'
          : 'bg-red-50 border border-red-200 text-red-700',
      ]"
    >
      <span class="text-base shrink-0">{{ incompleteFlag ? '⚠' : '❗' }}</span>
      <div class="flex-1">
        <p class="font-medium">
          {{ incompleteFlag
            ? 'Phiếu thiếu hồ sơ — đã đánh dấu cho phép duyệt'
            : 'Còn thiếu hồ sơ bắt buộc' }}
        </p>
        <p class="text-xs mt-0.5">{{ missingMandatory.join(' · ') }}</p>
        <p v-if="!incompleteFlag" class="text-xs mt-1 italic">
          → Có thể duyệt nếu đánh dấu '☑ Thiếu hồ sơ — vẫn cho phép duyệt' bên dưới và ghi rõ kế hoạch bổ sung.
        </p>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!documents.length" class="text-center py-8 text-slate-400 border-2 border-dashed border-slate-200 rounded-lg">
      <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="text-sm">Chưa có hồ sơ — bấm "+ Thêm hồ sơ" để khởi tạo</p>
    </div>

    <!-- Document list -->
    <div v-else class="space-y-2">
      <div
        v-for="doc in documents"
        :key="doc.idx"
        :class="[
          'rounded-lg border transition-colors',
          doc.status === 'Received' || doc.status === 'Waived'
            ? 'bg-green-50/40 border-green-200'
            : doc.is_mandatory
              ? 'bg-orange-50/40 border-orange-200'
              : 'bg-white border-slate-200',
        ]"
      >
        <!-- Compact row -->
        <div class="flex items-center gap-2 p-3">
          <!-- Drag handle / checkbox -->
          <button
            type="button"
            class="text-slate-400 hover:text-slate-600 shrink-0"
            :title="expanded.has(doc.idx) ? 'Thu gọn' : 'Mở rộng để sửa'"
            @click="toggleExpand(doc.idx)"
          >
            <svg class="w-4 h-4 transition-transform" :class="expanded.has(doc.idx) ? 'rotate-90' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <!-- Doc type select -->
          <select
            :value="doc.doc_type"
            :disabled="readonly"
            class="form-select text-sm flex-1 min-w-0"
            @change="updateField(doc.idx, 'doc_type', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="t in DOC_TYPE_OPTIONS" :key="t" :value="t">{{ t }}</option>
            <option v-if="!DOC_TYPE_OPTIONS.includes(doc.doc_type)" :value="doc.doc_type">{{ doc.doc_type }}</option>
          </select>

          <!-- Mandatory toggle -->
          <label class="flex items-center gap-1 text-xs text-slate-600 shrink-0 whitespace-nowrap" :title="doc.is_mandatory ? 'Bắt buộc' : 'Tùy chọn'">
            <input
              type="checkbox"
              :checked="doc.is_mandatory === 1"
              :disabled="readonly"
              class="rounded"
              @change="updateField(doc.idx, 'is_mandatory', ($event.target as HTMLInputElement).checked ? 1 : 0)"
            />
            Bắt buộc
          </label>

          <!-- Status select -->
          <select
            :value="doc.status"
            :disabled="readonly"
            class="form-select text-xs shrink-0 w-28"
            :class="STATUS_CLASS[doc.status] || ''"
            @change="updateField(doc.idx, 'status', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>

          <!-- Remove button -->
          <button
            v-if="!readonly"
            type="button"
            class="text-red-500 hover:text-red-700 shrink-0 px-1"
            title="Xóa hàng này"
            @click="emit('remove', doc.idx)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3" />
            </svg>
          </button>
        </div>

        <!-- Expanded detail row -->
        <div v-if="expanded.has(doc.idx)" class="px-3 pb-3 grid grid-cols-1 md:grid-cols-2 gap-3 border-t border-slate-100 pt-3">
          <div>
            <label class="block text-xs text-slate-500 mb-0.5">Số tài liệu</label>
            <input
              type="text"
              :value="doc.doc_number || ''"
              :disabled="readonly"
              class="form-input text-sm w-full"
              placeholder="VD: CO/2026/001"
              @change="updateField(doc.idx, 'doc_number', ($event.target as HTMLInputElement).value)"
            />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-0.5">Ngày nhận</label>
            <input
              type="date"
              :value="doc.received_date || ''"
              :disabled="readonly"
              class="form-input text-sm w-full"
              @change="updateField(doc.idx, 'received_date', ($event.target as HTMLInputElement).value)"
            />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-0.5">Ngày hết hạn</label>
            <input
              type="date"
              :value="doc.expiry_date || ''"
              :disabled="readonly"
              class="form-input text-sm w-full"
              @change="updateField(doc.idx, 'expiry_date', ($event.target as HTMLInputElement).value)"
            />
            <p v-if="doc.expiry_date" class="text-xs mt-0.5" :class="expiryClass(doc.expiry_date)">
              {{ expiryLabel(doc.expiry_date) }}
            </p>
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-0.5">File đính kèm (URL)</label>
            <input
              type="text"
              :value="doc.file_url || ''"
              :disabled="readonly"
              class="form-input text-sm w-full font-mono"
              placeholder="/files/..."
              @change="updateField(doc.idx, 'file_url', ($event.target as HTMLInputElement).value)"
            />
            <a v-if="doc.file_url" :href="doc.file_url" target="_blank" rel="noopener"
               class="text-blue-600 text-xs hover:underline mt-1 inline-block">📎 Mở file</a>
          </div>
          <div class="md:col-span-2">
            <label class="block text-xs text-slate-500 mb-0.5">Ghi chú</label>
            <input
              type="text"
              :value="doc.remarks || ''"
              :disabled="readonly"
              class="form-input text-sm w-full"
              placeholder="Ghi chú riêng cho hồ sơ này..."
              @change="updateField(doc.idx, 'remarks', ($event.target as HTMLInputElement).value)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
