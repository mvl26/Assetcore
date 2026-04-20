<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h3>Đánh dấu Miễn đăng ký NĐ98</h3>

      <div class="info-box">
        <strong>Thiết bị:</strong> {{ modelValue.asset_ref }}<br/>
        <strong>Loại tài liệu:</strong> {{ modelValue.doc_type_detail }}
      </div>

      <p class="notice">
        Chỉ áp dụng cho thiết bị được Bộ Y tế miễn đăng ký lưu hành theo Nghị định 98/2021/NĐ-CP.
        Yêu cầu có văn bản miễn đăng ký chính thức.
      </p>

      <div class="field-group">
        <label>Lý do miễn đăng ký <span class="req">*</span></label>
        <textarea
          v-model="form.exempt_reason"
          rows="3"
          class="input"
          placeholder="VD: Thiết bị sản xuất trong nước không thuộc danh mục phải đăng ký..."
        ></textarea>
      </div>

      <div class="field-group">
        <label>Văn bản miễn đăng ký (file URL) <span class="req">*</span></label>
        <input
          v-model="form.exempt_proof"
          class="input"
          placeholder="/files/mien-dang-ky-xxx.pdf"
        />
        <small class="hint">Upload file trước qua Files, rồi dán đường dẫn vào đây.</small>
      </div>

      <div v-if="error" class="alert-danger">{{ error }}</div>

      <div class="modal-actions">
        <button class="btn btn-outline" @click="$emit('close')">Hủy</button>
        <button
          class="btn btn-warning"
          :disabled="!form.exempt_reason || !form.exempt_proof || loading"
          @click="handleSubmit"
        >
          {{ loading ? 'Đang xử lý...' : 'Xác nhận Exempt' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { markExempt } from '@/api/imm05'
import type { AssetDocumentItem } from '@/api/imm05'

const props = defineProps<{ modelValue: AssetDocumentItem }>()
const emit = defineEmits<{ close: []; exempted: [docName: string] }>()

const loading = ref(false)
const error = ref('')
const form = reactive({ exempt_reason: '', exempt_proof: '' })

async function handleSubmit() {
  if (!form.exempt_reason || !form.exempt_proof) return
  loading.value = true
  error.value = ''
  try {
    const res = await markExempt({
      asset_ref: props.modelValue.asset_ref,
      doc_type_detail: props.modelValue.doc_type_detail,
      exempt_reason: form.exempt_reason,
      exempt_proof: form.exempt_proof,
    })
    const r = res as unknown as { document_name?: string } | null
    if (r?.document_name) emit('exempted', r.document_name)
    else error.value = 'Đánh dấu Exempt thất bại'
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal { background: white; border-radius: 10px; padding: 1.5rem; width: 460px; max-width: 95vw; }
.modal h3 { margin: 0 0 1rem; font-size: 1.1rem; }
.info-box { background: #f9fafb; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem; font-size: 0.85rem; line-height: 1.6; }
.notice { font-size: 0.8rem; color: #92400e; background: #fef3c7; padding: 0.6rem 0.75rem; border-radius: 6px; margin-bottom: 1rem; }
.field-group { margin-bottom: 0.875rem; display: flex; flex-direction: column; gap: 4px; }
label { font-size: 0.8rem; font-weight: 500; color: #374151; }
.req { color: #ef4444; }
.hint { font-size: 0.75rem; color: #9ca3af; }
.input { padding: 0.4rem 0.6rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.875rem; width: 100%; box-sizing: border-box; }
.alert-danger { padding: 0.5rem 0.75rem; background: #fee2e2; color: #991b1b; border-radius: 4px; font-size: 0.8rem; margin-bottom: 0.75rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1rem; }
.btn { padding: 0.45rem 1rem; border-radius: 4px; border: none; cursor: pointer; font-size: 0.875rem; }
.btn-warning { background: #f59e0b; color: white; }
.btn-warning:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { background: transparent; border: 1px solid #d1d5db; }
</style>
