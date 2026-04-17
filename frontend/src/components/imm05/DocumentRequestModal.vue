<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <h3>Tạo Yêu cầu Bổ sung Tài liệu</h3>

      <div class="field-group">
        <label>Thiết bị</label>
        <input :value="modelValue.asset_ref" disabled class="input" />
      </div>

      <div class="field-group">
        <label>Loại tài liệu cần bổ sung <span class="req">*</span></label>
        <input
          v-model="form.doc_type_required"
          placeholder="VD: Chứng nhận đăng ký lưu hành"
          class="input"
        />
      </div>

      <div class="field-row">
        <div class="field-group">
          <label>Nhóm tài liệu</label>
          <select v-model="form.doc_category" class="input">
            <option value="Legal">Pháp lý</option>
            <option value="Technical">Kỹ thuật</option>
            <option value="Certification">Kiểm định</option>
            <option value="Training">Đào tạo</option>
            <option value="QA">Chất lượng</option>
          </select>
        </div>
        <div class="field-group">
          <label>Mức độ ưu tiên</label>
          <select v-model="form.priority" class="input">
            <option value="Low">Thấp</option>
            <option value="Medium">Trung bình</option>
            <option value="High">Cao</option>
            <option value="Critical">Khẩn cấp</option>
          </select>
        </div>
      </div>

      <div class="field-group">
        <label>Giao cho</label>
        <input v-model="form.assigned_to" placeholder="Email người thực hiện" class="input" />
      </div>

      <div class="field-group">
        <label>Hạn hoàn thành</label>
        <input v-model="form.due_date" type="date" class="input" />
      </div>

      <div class="field-group">
        <label>Ghi chú</label>
        <textarea v-model="form.request_note" rows="2" class="input" placeholder="Lý do yêu cầu..."></textarea>
      </div>

      <div v-if="error" class="alert-danger">{{ error }}</div>

      <div class="modal-actions">
        <button class="btn btn-outline" @click="$emit('close')">Hủy</button>
        <button
          class="btn btn-primary"
          :disabled="!form.doc_type_required || loading"
          @click="handleSubmit"
        >
          {{ loading ? 'Đang tạo...' : 'Tạo yêu cầu' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useImm05Store } from '@/stores/imm05Store'
import type { AssetDocumentItem } from '@/api/imm05'

const props = defineProps<{ modelValue: AssetDocumentItem }>()
const emit = defineEmits<{ close: []; created: [name: string] }>()

const store = useImm05Store()
const loading = ref(false)
const error = ref('')

const today = new Date()
today.setDate(today.getDate() + 30)
const defaultDue = today.toISOString().split('T')[0]

const form = reactive({
  doc_type_required: props.modelValue.doc_type_detail,
  doc_category: props.modelValue.doc_category || 'Legal',
  priority: 'Medium',
  assigned_to: '',
  due_date: defaultDue,
  request_note: '',
})

async function handleSubmit() {
  if (!form.doc_type_required) return
  loading.value = true
  error.value = ''
  const name = await store.createRequest({
    asset_ref: props.modelValue.asset_ref,
    doc_type_required: form.doc_type_required,
    doc_category: form.doc_category,
    assigned_to: form.assigned_to,
    due_date: form.due_date,
    priority: form.priority,
    request_note: form.request_note,
    source_type: 'Dashboard',
  })
  loading.value = false
  if (name) {
    emit('created', name)
  } else {
    error.value = store.error ?? 'Tạo yêu cầu thất bại'
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal { background: white; border-radius: 10px; padding: 1.5rem; width: 480px; max-width: 95vw; }
.modal h3 { margin: 0 0 1.25rem; font-size: 1.1rem; }
.field-group { margin-bottom: 0.875rem; display: flex; flex-direction: column; gap: 4px; }
.field-row { display: flex; gap: 0.75rem; }
.field-row .field-group { flex: 1; }
label { font-size: 0.8rem; font-weight: 500; color: #374151; }
.req { color: #ef4444; }
.input {
  padding: 0.4rem 0.6rem; border: 1px solid #d1d5db;
  border-radius: 4px; font-size: 0.875rem; width: 100%; box-sizing: border-box;
}
.input:disabled { background: #f9fafb; color: #9ca3af; }
.alert-danger { padding: 0.5rem 0.75rem; background: #fee2e2; color: #991b1b; border-radius: 4px; font-size: 0.8rem; margin-bottom: 0.75rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1rem; }
.btn { padding: 0.45rem 1rem; border-radius: 4px; border: none; cursor: pointer; font-size: 0.875rem; }
.btn-primary { background: #4f8ef7; color: white; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { background: transparent; border: 1px solid #d1d5db; }
</style>
