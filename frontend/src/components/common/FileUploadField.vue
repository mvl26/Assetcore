<script setup lang="ts">
/**
 * Ô đính kèm tệp dùng chung cho MỌI field Attach / Attach Image.
 *
 * Thay thế hoàn toàn kiểu cũ `<input type="text" placeholder="/files/...">` —
 * bắt người dùng gõ đường dẫn là lỗi nghiệp vụ: tệp không vào hệ thống, không có
 * bản ghi File, không có quyền, hồ sơ NĐ98 mất bằng chứng.
 *
 * v-model là `file_url` do máy chủ trả về sau khi tải lên thành công.
 */
import { computed, ref } from 'vue'

import { fileNameFromUrl, uploadAttachment } from '@/api/files'

const props = withDefaults(defineProps<{
  /** file_url đã lưu (v-model). */
  modelValue: string
  /** DocType chứa field đính kèm (có thể là bảng con). */
  doctype: string
  /** Tên field Attach / Attach Image. */
  fieldname: string
  /** Bản ghi cha để gắn tệp — bỏ trống ở màn hình tạo mới. */
  docname?: string
  /** DocType cha — bắt buộc khi `doctype` là bảng con. */
  parentDoctype?: string
  /** Nhãn hiển thị phía trên ô. */
  label?: string
  /** Bộ lọc định dạng cho hộp thoại chọn tệp. */
  accept?: string
  /** Chỉ nhận ảnh (hiện ảnh xem trước). */
  image?: boolean
  disabled?: boolean
  /** Gợi ý hiển thị khi chưa có tệp. */
  hint?: string
}>(), {
  docname: '',
  parentDoctype: '',
  label: '',
  accept: '.pdf,.doc,.docx,.xls,.xlsx,.csv,.png,.jpg,.jpeg,.webp',
  image: false,
  disabled: false,
  hint: '',
})

const emit = defineEmits<{ 'update:modelValue': [string] }>()

const uploading = ref(false)
const error = ref('')

const acceptAttr = computed(() => (props.image ? 'image/*' : props.accept))
const displayName = computed(() => fileNameFromUrl(props.modelValue))
const placeholderHint = computed(() =>
  props.hint || (props.image
    ? 'Bấm để chọn ảnh (jpg, png, webp — tối đa 5MB)'
    : 'Bấm để chọn tệp (pdf, doc, xls, ảnh — tối đa 10MB)'),
)

async function onChange(evt: Event) {
  const input = evt.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  error.value = ''
  uploading.value = true
  try {
    const res = await uploadAttachment(file, {
      doctype: props.doctype,
      fieldname: props.fieldname,
      docname: props.docname,
      parentDoctype: props.parentDoctype,
    })
    emit('update:modelValue', res.file_url)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Tải tệp lên thất bại'
  } finally {
    uploading.value = false
    // Cho phép chọn lại CÙNG tệp sau khi lỗi/xoá.
    input.value = ''
  }
}

function clearFile() {
  error.value = ''
  emit('update:modelValue', '')
}
</script>

<template>
  <div>
    <label v-if="label" class="form-label">{{ label }}</label>

    <!-- Đã có tệp -->
    <div
      v-if="modelValue"
      class="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-200 bg-gray-50"
    >
      <img
        v-if="image"
        :src="modelValue"
        alt="Ảnh đã tải lên"
        class="w-12 h-12 rounded object-cover border border-slate-200 flex-shrink-0"
      />
      <svg
        v-else class="w-5 h-5 text-gray-500 flex-shrink-0" fill="none"
        stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round" stroke-linejoin="round"
          d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.122 2.122l7.81-7.81"
        />
      </svg>
      <a
        :href="modelValue" target="_blank" rel="noopener"
        class="flex-1 min-w-0 text-sm text-blue-600 hover:underline truncate"
        :title="displayName"
      >{{ displayName }}</a>
      <label
        v-if="!disabled"
        class="text-xs text-gray-600 hover:text-blue-600 cursor-pointer flex-shrink-0"
      >
        <input
          type="file" class="hidden" :accept="acceptAttr"
          :disabled="uploading" @change="onChange"
        />
        {{ uploading ? 'Đang tải…' : 'Thay tệp' }}
      </label>
      <button
        v-if="!disabled" type="button"
        class="text-gray-400 hover:text-red-600 text-xs flex-shrink-0"
        title="Gỡ tệp" @click="clearFile"
      >
        ✕
      </button>
    </div>

    <!-- Chưa có tệp -->
    <label
      v-else
      class="flex items-center justify-center gap-2 h-11 border-2 border-dashed rounded-lg transition-colors"
      :class="disabled
        ? 'border-gray-200 bg-gray-50 cursor-not-allowed text-gray-400'
        : 'border-gray-300 cursor-pointer hover:bg-gray-50 hover:border-gray-400'"
    >
      <input
        type="file" class="hidden" :accept="acceptAttr"
        :disabled="disabled || uploading" @change="onChange"
      />
      <svg
        v-if="!uploading" class="w-4 h-4 text-gray-400" fill="none"
        stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round" stroke-linejoin="round"
          d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-.41-8.98 4.5 4.5 0 018.4-2.09A4.5 4.5 0 0117.25 19.5H6.75z"
        />
      </svg>
      <span class="text-xs text-gray-500">
        {{ uploading ? 'Đang tải lên…' : placeholderHint }}
      </span>
    </label>

    <p v-if="error" class="text-xs text-red-600 mt-1" role="alert">{{ error }}</p>
  </div>
</template>
