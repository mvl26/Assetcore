<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm05Store } from '@/stores/imm05Store'
import { uploadDocumentFile } from '@/api/imm05'
import SmartSelect from '@/components/common/SmartSelect.vue'

const router = useRouter()
const route = useRoute()
const store = useImm05Store()

// Pre-fill asset_ref từ query param (?asset=...) nếu được navigate từ IMM-04
const initialAsset = (route.query.asset as string) ?? ''
// Pre-fill doc_type_detail từ query param (?doc_type_detail=...) nếu navigate từ "Upload phiên bản mới"
const initialDocType = (route.query.doc_type_detail as string) ?? ''
// Pre-fill version từ query (?version=N.M) khi flow Upload-new-version từ DocumentDetail
const initialVersion = (route.query.version as string) || '1.0'

const form = reactive({
  asset_ref: initialAsset,
  doc_category: 'Legal' as string,
  doc_type_detail: initialDocType,
  doc_number: '',
  version: initialVersion,
  issued_date: '',
  expiry_date: '',
  issuing_authority: '',
  file_attachment: '',
  change_summary: '',
  visibility: 'Public' as 'Public' | 'Internal_Only',
  notes: '',
  // Task 3a: Exempt fields
  is_exempt: 0 as 0 | 1,
  exempt_reason: '',
  exempt_proof: '',
  // Task 3b: Model-level flag
  is_model_level: 0 as 0 | 1,
})

// File upload state
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const fileError = ref('')

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  fileError.value = ''
  if (!file) return

  const allowedTypes = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ]
  if (!allowedTypes.includes(file.type)) {
    fileError.value = 'VR-08: Chỉ chấp nhận file PDF, JPG, PNG, DOCX.'
    selectedFile.value = null
    return
  }
  if (file.size > 25 * 1024 * 1024) {
    fileError.value = 'File không được vượt quá 25MB.'
    selectedFile.value = null
    return
  }
  selectedFile.value = file
}


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

/** Returns a validation error message or null if valid. */
function validateForm(): string | null {
  // asset_ref is optional when is_model_level = 1 (Task 3b)
  const assetRequired = form.is_model_level !== 1
  if ((assetRequired && !form.asset_ref) || !form.doc_type_detail || !form.doc_number || !form.issued_date) {
    return 'Vui lòng điền đầy đủ các trường bắt buộc (*).'
  }
  if (form.is_exempt === 1 && !form.exempt_reason.trim()) {
    return 'Vui lòng nhập Lý do miễn khi đánh dấu Miễn đăng ký NĐ98.'
  }
  if (form.expiry_date && form.issued_date && form.expiry_date <= form.issued_date) {
    return 'VR-01: Ngày hết hạn phải sau ngày phát hành.'
  }
  if (form.version && form.version !== '1.0' && !form.change_summary?.trim()) {
    return 'VR-09: Cần nhập tóm tắt thay đổi khi phiên bản > 1.0.'
  }
  if (['Legal', 'Certification'].includes(form.doc_category) && !form.expiry_date) {
    return 'Tài liệu Pháp lý / Kiểm định bắt buộc có Ngày hết hạn.'
  }
  if (form.doc_category === 'Legal' && !form.issuing_authority) {
    return 'Tài liệu Pháp lý bắt buộc điền Cơ quan cấp.'
  }
  return null
}

function buildPayload(fileUrl: string): Record<string, unknown> {
  const payload: Record<string, unknown> = { ...form, file_attachment: fileUrl }
  const optionalFields = ['expiry_date', 'issuing_authority', 'notes', 'file_attachment', 'change_summary', 'exempt_reason', 'exempt_proof'] as const
  for (const field of optionalFields) {
    if (!payload[field]) delete payload[field]
  }
  return payload
}

async function handleSubmit() {
  error.value = null
  const validationError = validateForm()
  if (validationError) {
    error.value = validationError
    return
  }

  saving.value = true
  try {
    // Upload file trước nếu người dùng đã chọn file
    let fileUrl = form.file_attachment
    if (selectedFile.value) {
      try {
        const uploaded = await uploadDocumentFile(selectedFile.value, { isPrivate: false })
        fileUrl = uploaded.file_url
      } catch (uploadErr) {
        error.value = uploadErr instanceof Error ? uploadErr.message : 'Upload file thất bại. Vui lòng thử lại.'
        saving.value = false
        return
      }
    }

    const payload = buildPayload(fileUrl)
    const res = await store.createDocument(payload)
    saving.value = false
    const r = res as unknown as { name?: string } | null
    if (r?.name) {
      router.push({ path: '/documents', query: form.asset_ref ? { asset: form.asset_ref } : {} })
    } else {
      error.value = store.error ?? 'Tạo tài liệu thất bại'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
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
          <label for="field-asset-ref">
            Mã thiết bị
            <span v-if="form.is_model_level !== 1" class="required">*</span>
          </label>
          <SmartSelect
            v-model="form.asset_ref"
            doctype="AC Asset"
            placeholder="Tìm thiết bị theo tên / mã / serial..."
          />
          <small>Tìm thiết bị; tự gợi ý khi gõ tên hoặc serial</small>
        </div>

        <!-- is_model_level (Task 3b) -->
        <div class="form-field form-field-toggle">
          <label class="toggle-label">
            <input
              v-model="form.is_model_level"
              type="checkbox"
              :true-value="1"
              :false-value="0"
              class="toggle-checkbox"
            />
            <span>Tài liệu áp dụng cho toàn dòng thiết bị (is_model_level)</span>
          </label>
          <small v-if="form.is_model_level === 1" class="model-level-hint">
            Hồ sơ này sẽ áp dụng cho tất cả tài sản cùng Model
          </small>
        </div>

        <!-- Doc Category -->
        <div class="form-field">
          <label for="field-doc-category">Nhóm tài liệu <span class="required">*</span></label>
          <select id="field-doc-category" v-model="form.doc_category" class="input" @change="onCategoryChange">
            <option value="Legal">Pháp lý</option>
            <option value="Technical">Kỹ thuật</option>
            <option value="Certification">Kiểm định</option>
            <option value="Training">Đào tạo</option>
            <option value="QA">Chất lượng</option>
          </select>
        </div>

        <!-- Doc Type Detail -->
        <div class="form-field form-field-wide">
          <label for="field-doc-type">Loại tài liệu <span class="required">*</span></label>
          <input
            id="field-doc-type"
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
          <label for="field-doc-number">Số hiệu tài liệu <span class="required">*</span></label>
          <input id="field-doc-number" v-model="form.doc_number" type="text" placeholder="VD: VN-REG-2026-001" class="input" />
        </div>

        <!-- Version -->
        <div class="form-field">
          <label for="field-version">Phiên bản <span class="required">*</span></label>
          <input id="field-version" v-model="form.version" type="text" placeholder="1.0" class="input" />
        </div>

        <!-- Issued Date -->
        <div class="form-field">
          <label for="field-issued-date">Ngày cấp <span class="required">*</span></label>
          <input id="field-issued-date" v-model="form.issued_date" type="date" class="input" />
        </div>

        <!-- Expiry Date -->
        <div class="form-field">
          <label for="field-expiry-date">
            Ngày hết hạn
            <span v-if="['Legal','Certification'].includes(form.doc_category)" class="required">*</span>
          </label>
          <input id="field-expiry-date" v-model="form.expiry_date" type="date" class="input" />
        </div>

        <!-- Issuing Authority -->
        <div class="form-field">
          <label for="field-issuing-authority">
            Cơ quan cấp
            <span v-if="form.doc_category === 'Legal'" class="required">*</span>
          </label>
          <input
            id="field-issuing-authority"
            v-model="form.issuing_authority"
            type="text"
            placeholder="Bộ Y tế / Cục Quản lý Dược..."
            class="input"
          />
        </div>

        <!-- File Attachment Upload -->
        <div class="form-field form-field-wide">
          <label for="field-file-attachment">File đính kèm <span class="required">*</span></label>
          <input
            id="field-file-attachment"
            ref="fileInputRef"
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.docx"
            class="input"
            @change="handleFileSelect"
          />
          <small>Định dạng: PDF, JPG, PNG, DOCX. Tối đa 25MB.</small>
          <div v-if="selectedFile" class="mt-1 text-success">&#10003; {{ selectedFile.name }}</div>
          <div v-if="fileError" class="mt-1 text-file-error">{{ fileError }}</div>
        </div>

        <!-- Change Summary (VR-09: bắt buộc khi version != 1.0) -->
        <div class="form-field form-field-wide">
          <label for="field-change-summary">
            Tóm tắt thay đổi
            <span v-if="form.version && form.version !== '1.0'" class="required">*</span>
          </label>
          <textarea
            id="field-change-summary"
            v-model="form.change_summary"
            rows="2"
            placeholder="Mô tả thay đổi so với phiên bản trước (bắt buộc khi phiên bản > 1.0)..."
            class="input"
          />
        </div>

        <!-- Visibility -->
        <div class="form-field">
          <label for="field-visibility">Phạm vi hiển thị</label>
          <select id="field-visibility" v-model="form.visibility" class="input">
            <option value="Public">Công khai (Public)</option>
            <option value="Internal_Only">Nội bộ (Internal Only)</option>
          </select>
        </div>

        <!-- Notes -->
        <div class="form-field form-field-wide">
          <label for="field-notes">Ghi chú</label>
          <textarea id="field-notes" v-model="form.notes" rows="3" placeholder="Ghi chú thêm..." class="input" />
        </div>

        <!-- is_exempt toggle (Task 3a) -->
        <div class="form-field form-field-wide">
          <label class="toggle-label">
            <input
              v-model="form.is_exempt"
              type="checkbox"
              :true-value="1"
              :false-value="0"
              class="toggle-checkbox"
            />
            <span>Miễn đăng ký NĐ98 (is_exempt)</span>
          </label>
          <template v-if="form.is_exempt === 1">
            <div class="exempt-sub-fields">
              <div class="form-field">
                <label for="field-exempt-reason">Lý do miễn <span class="required">*</span></label>
                <textarea
                  id="field-exempt-reason"
                  v-model="form.exempt_reason"
                  rows="2"
                  placeholder="Nêu lý do miễn đăng ký..."
                  class="input"
                />
              </div>
              <div class="form-field">
                <label for="field-exempt-proof">Bằng chứng miễn</label>
                <input
                  id="field-exempt-proof"
                  v-model="form.exempt_proof"
                  type="text"
                  placeholder="URL hoặc mã tài liệu bằng chứng..."
                  class="input"
                />
              </div>
            </div>
          </template>
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
.create-view { padding: 1.75rem 1.5rem; width: 100%; }

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

/* File upload feedback */
.mt-1 { margin-top: 0.25rem; }
.text-success { font-size: 0.8rem; color: #16a34a; }
.text-file-error { font-size: 0.8rem; color: #dc2626; }

/* Toggle / checkbox fields */
.form-field-toggle { grid-column: span 2; }
.toggle-label {
  display: inline-flex; align-items: center; gap: 0.5rem;
  cursor: pointer; font-size: 0.875rem; color: #374151;
}
.toggle-checkbox { width: 1rem; height: 1rem; cursor: pointer; accent-color: #2563eb; }
.model-level-hint { color: #4f8ef7; }
.exempt-sub-fields {
  margin-top: 0.75rem; padding: 0.75rem;
  background: #f0fdf4; border-radius: 6px; border: 1px solid #bbf7d0;
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;
}

@media (max-width: 600px) {
  .form-grid { grid-template-columns: 1fr; }
  .form-field-wide { grid-column: span 1; }
  .form-field-toggle { grid-column: span 1; }
  .exempt-sub-fields { grid-template-columns: 1fr; }
}
</style>
