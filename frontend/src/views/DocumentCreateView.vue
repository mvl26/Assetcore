<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createDocument } from '@/api/imm05'

const router = useRouter()
const route = useRoute()

// Pre-fill asset_ref từ query param (?asset=...) nếu được navigate từ IMM-04
const initialAsset = (route.query.asset as string) ?? ''

const form = reactive({
  asset_ref: initialAsset,
  doc_category: 'Legal' as string,
  doc_type_detail: '',
  doc_number: '',
  version: '1.0',
  issued_date: '',
  expiry_date: '',
  issuing_authority: '',
  file_attachment: '',
  visibility: 'Public' as 'Public' | 'Internal_Only',
  notes: '',
})

const saving = ref(false)
const error = ref<string | null>(null)

// Danh sách loại tài liệu gợi ý theo category
const DOC_TYPE_SUGGESTIONS: Record<string, string[]> = {
  Legal: ['Chứng nhận đăng ký lưu hành', 'Giấy phép nhập khẩu', 'Giấy phép bức xạ'],
  Technical: ['Hướng dẫn sử dụng (IFU)', 'Tài liệu kỹ thuật / Service Manual'],
  Certification: ['Chứng chỉ hiệu chuẩn', 'Biên bản kiểm tra an toàn'],
  Training: ['Chứng nhận đào tạo người dùng'],
  QA: ['Hợp đồng bảo hành / bảo trì'],
}

const suggestions = ref<string[]>(DOC_TYPE_SUGGESTIONS['Legal'])

function onCategoryChange() {
  suggestions.value = DOC_TYPE_SUGGESTIONS[form.doc_category] ?? []
  form.doc_type_detail = ''
}

function selectSuggestion(s: string) {
  form.doc_type_detail = s
}

async function handleSubmit() {
  error.value = null
  if (!form.asset_ref || !form.doc_type_detail || !form.doc_number || !form.issued_date) {
    error.value = 'Vui lòng điền đầy đủ các trường bắt buộc (*).'
    return
  }

  // Legal/Certification bắt buộc expiry_date (VR-07)
  if (['Legal', 'Certification'].includes(form.doc_category) && !form.expiry_date) {
    error.value = 'Tài liệu Pháp lý / Kiểm định bắt buộc có Ngày hết hạn.'
    return
  }

  // Legal bắt buộc issuing_authority (VR-04)
  if (form.doc_category === 'Legal' && !form.issuing_authority) {
    error.value = 'Tài liệu Pháp lý bắt buộc điền Cơ quan cấp.'
    return
  }

  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form }
    // Loại bỏ field rỗng để tránh lỗi validate
    if (!payload.expiry_date) delete payload.expiry_date
    if (!payload.issuing_authority) delete payload.issuing_authority
    if (!payload.notes) delete payload.notes
    if (!payload.file_attachment) delete payload.file_attachment

    const res = await createDocument(payload)
    if (res.success) {
      router.push({
        path: '/documents',
        query: form.asset_ref ? { asset: form.asset_ref } : {},
      })
    } else {
      error.value = res.error ?? 'Tạo tài liệu thất bại'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.back()
}
</script>

<template>
  <div class="create-view">
    <!-- Header -->
    <div class="page-header">
      <div>
        <button class="back-btn" @click="goBack">← Quay lại</button>
        <h1>Tải lên Tài liệu Mới</h1>
      </div>
    </div>

    <!-- Form -->
    <div class="form-card">
      <!-- Error -->
      <div v-if="error" class="alert alert-danger">{{ error }}</div>

      <div class="form-grid">
        <!-- Asset Ref -->
        <div class="form-field">
          <label>Mã thiết bị <span class="required">*</span></label>
          <input
            v-model="form.asset_ref"
            type="text"
            placeholder="ACC-ASS-2026-xxxxx"
            class="input"
          />
          <small>Nhập mã asset chính xác (ví dụ: ACC-ASS-2026-00007)</small>
        </div>

        <!-- Doc Category -->
        <div class="form-field">
          <label>Nhóm tài liệu <span class="required">*</span></label>
          <select v-model="form.doc_category" class="input" @change="onCategoryChange">
            <option value="Legal">Pháp lý</option>
            <option value="Technical">Kỹ thuật</option>
            <option value="Certification">Kiểm định</option>
            <option value="Training">Đào tạo</option>
            <option value="QA">Chất lượng</option>
          </select>
        </div>

        <!-- Doc Type Detail -->
        <div class="form-field form-field-wide">
          <label>Loại tài liệu <span class="required">*</span></label>
          <input
            v-model="form.doc_type_detail"
            type="text"
            placeholder="Tên loại tài liệu..."
            class="input"
          />
          <!-- Gợi ý nhanh -->
          <div v-if="suggestions.length" class="suggestions">
            <button
              v-for="s in suggestions"
              :key="s"
              class="suggestion-chip"
              :class="{ active: form.doc_type_detail === s }"
              type="button"
              @click="selectSuggestion(s)"
            >{{ s }}</button>
          </div>
        </div>

        <!-- Doc Number -->
        <div class="form-field">
          <label>Số hiệu tài liệu <span class="required">*</span></label>
          <input v-model="form.doc_number" type="text" placeholder="VD: VN-REG-2026-001" class="input" />
        </div>

        <!-- Version -->
        <div class="form-field">
          <label>Phiên bản <span class="required">*</span></label>
          <input v-model="form.version" type="text" placeholder="1.0" class="input" />
        </div>

        <!-- Issued Date -->
        <div class="form-field">
          <label>Ngày cấp <span class="required">*</span></label>
          <input v-model="form.issued_date" type="date" class="input" />
        </div>

        <!-- Expiry Date -->
        <div class="form-field">
          <label>
            Ngày hết hạn
            <span v-if="['Legal','Certification'].includes(form.doc_category)" class="required">*</span>
          </label>
          <input v-model="form.expiry_date" type="date" class="input" />
        </div>

        <!-- Issuing Authority -->
        <div class="form-field">
          <label>
            Cơ quan cấp
            <span v-if="form.doc_category === 'Legal'" class="required">*</span>
          </label>
          <input
            v-model="form.issuing_authority"
            type="text"
            placeholder="Bộ Y tế / Cục Quản lý Dược..."
            class="input"
          />
        </div>

        <!-- File Attachment URL -->
        <div class="form-field form-field-wide">
          <label>Đường dẫn file</label>
          <input
            v-model="form.file_attachment"
            type="text"
            placeholder="/files/ten_file.pdf (upload qua Frappe Desk rồi điền path)"
            class="input"
          />
          <small>
            Upload file trên Frappe Desk trước:
            <a href="/app/upload" target="_blank">Mở File Manager →</a>
          </small>
        </div>

        <!-- Visibility -->
        <div class="form-field">
          <label>Phạm vi hiển thị</label>
          <select v-model="form.visibility" class="input">
            <option value="Public">Công khai (Public)</option>
            <option value="Internal_Only">Nội bộ (Internal Only)</option>
          </select>
        </div>

        <!-- Notes -->
        <div class="form-field form-field-wide">
          <label>Ghi chú</label>
          <textarea v-model="form.notes" rows="3" placeholder="Ghi chú thêm..." class="input" />
        </div>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <button class="btn btn-outline" :disabled="saving" @click="goBack">Hủy</button>
        <button class="btn btn-primary" :disabled="saving" @click="handleSubmit">
          <span v-if="saving">Đang lưu...</span>
          <span v-else>Lưu tài liệu (Draft)</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-view { padding: 1.5rem; max-width: 860px; margin: 0 auto; }

.page-header { margin-bottom: 1.5rem; }
.page-header h1 { margin: 0.25rem 0 0; font-size: 1.4rem; }
.back-btn {
  background: none; border: none; cursor: pointer;
  color: #6b7280; font-size: 0.875rem; padding: 0;
}
.back-btn:hover { color: #111827; }

.form-card {
  background: white; border-radius: 8px;
  border: 1px solid #e5e7eb; padding: 1.5rem;
}

.form-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 1.25rem; margin-bottom: 1.5rem;
}
.form-field { display: flex; flex-direction: column; gap: 4px; }
.form-field-wide { grid-column: span 2; }

label { font-size: 0.875rem; font-weight: 500; color: #374151; }
.required { color: #ef4444; }

.input {
  padding: 0.5rem 0.75rem; border: 1px solid #d1d5db;
  border-radius: 4px; font-size: 0.875rem; width: 100%;
  box-sizing: border-box;
}
.input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 2px #dbeafe; }
textarea.input { resize: vertical; font-family: inherit; }
small { font-size: 0.75rem; color: #9ca3af; }
small a { color: #2563eb; }

/* Suggestions */
.suggestions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.suggestion-chip {
  padding: 2px 10px; border-radius: 12px; font-size: 0.75rem;
  background: #f3f4f6; border: 1px solid #d1d5db;
  cursor: pointer; transition: all 0.1s;
}
.suggestion-chip:hover { background: #dbeafe; border-color: #93c5fd; color: #1e40af; }
.suggestion-chip.active { background: #2563eb; color: white; border-color: #2563eb; }

/* Actions */
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn { padding: 0.5rem 1.25rem; border-radius: 4px; border: none; cursor: pointer; font-size: 0.875rem; font-weight: 500; }
.btn-primary { background: #2563eb; color: #ffffff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-outline { background: transparent; border: 1px solid #d1d5db; color: #374151; }
.btn-outline:hover:not(:disabled) { background: #f9fafb; }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }

/* Alert */
.alert { padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.alert-danger { background: #fee2e2; color: #991b1b; }

@media (max-width: 600px) {
  .form-grid { grid-template-columns: 1fr; }
  .form-field-wide { grid-column: span 1; }
}
</style>
