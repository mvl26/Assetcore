<template>
  <div class="needs-request-create">
    <div class="page-header">
      <h1>Tạo đề xuất nhu cầu thiết bị</h1>
      <button class="btn btn-outline" @click="$router.back()">← Quay lại</button>
    </div>

    <div v-if="store.error" class="alert alert-danger">
      <strong>Lỗi:</strong> {{ store.error }}
      <button class="alert-close" @click="store.clearError()">×</button>
    </div>

    <form class="form" @submit.prevent="onSubmit">
      <div class="grid-2col">
        <div class="card">
          <h3>1. Thông tin cơ bản</h3>
          <label>Loại đề xuất <span class="req">*</span>
            <select v-model="form.request_type" required>
              <option value="New">Mua mới</option>
              <option value="Replacement">Thay thế</option>
              <option value="Upgrade">Nâng cấp</option>
              <option value="Add-on">Bổ sung</option>
            </select>
          </label>
          <label>Khoa đề xuất <span class="req">*</span>
            <input v-model="form.requesting_department" type="text" required placeholder="Chọn khoa..." />
            <span class="hint">Khoa lâm sàng đề nghị mua sắm thiết bị</span>
          </label>
          <label>Trưởng khoa <span class="req">*</span>
            <input v-model="form.clinical_head" type="email" required placeholder="email@benhvien.vn" />
          </label>
        </div>

        <div class="card">
          <h3>2. Thiết bị muốn mua</h3>
          <label>Mẫu thiết bị <span class="req">*</span>
            <input v-model="form.device_model_ref" type="text" required placeholder="Chọn mẫu thiết bị..." />
          </label>
          <label>Số lượng <span class="req">*</span>
            <input v-model.number="form.quantity" type="number" min="1" required />
          </label>
          <label>Năm dự kiến mua <span class="req">*</span>
            <input v-model.number="form.target_year" type="number" :min="currentYear" required />
            <span class="hint">Phải từ năm {{ currentYear }} trở đi</span>
          </label>
          <label v-if="form.request_type === 'Replacement'">
            Thiết bị cần thay thế <span class="req">*</span>
            <input v-model="form.replacement_for_asset" type="text" placeholder="Chọn thiết bị..." />
            <span class="hint">Thiết bị thay thế phải có kế hoạch thanh lý đi kèm</span>
          </label>
        </div>
      </div>

      <div class="card">
        <h3>3. Lý do lâm sàng <span class="req">*</span></h3>
        <textarea v-model="form.clinical_justification" rows="6" required
                  placeholder="Mô tả nhu cầu lâm sàng, ảnh hưởng nếu không có thiết bị (tối thiểu 200 ký tự)..."></textarea>
        <div class="char-count">
          {{ (form.clinical_justification || '').length }} / 200 ký tự
          <span v-if="(form.clinical_justification || '').length < 200" class="error-text">
            (cần tối thiểu 200 ký tự)
          </span>
          <span v-else class="success-text">✓ đạt yêu cầu</span>
        </div>
      </div>

      <div v-if="form.request_type === 'Replacement' || form.request_type === 'Upgrade'" class="card">
        <h3>4. Dữ liệu sử dụng 12 tháng gần nhất</h3>
        <p class="hint">
          Bắt buộc với đề xuất thay thế / nâng cấp để hệ thống chấm điểm tín hiệu cần thay thế.
        </p>
        <div class="grid-2col">
          <label>Tỷ lệ sử dụng (%)
            <input v-model.number="form.utilization_pct_12m" type="number" step="0.01" min="0" max="100" />
          </label>
          <label>Thời gian ngừng hoạt động (giờ)
            <input v-model.number="form.downtime_hr_12m" type="number" step="0.1" min="0" />
          </label>
        </div>
      </div>

      <div class="action-bar">
        <button type="submit" class="btn btn-primary" :disabled="!canSubmit || submitting">
          {{ submitting ? 'Đang lưu...' : 'Tạo Draft' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import type { NeedsRequestDoc, RequestType } from '@/types/imm01'

const router = useRouter()
const store = useImm01Store()

const currentYear = new Date().getFullYear()
const submitting = ref(false)

const form = reactive<Partial<NeedsRequestDoc>>({
  request_type: 'New' as RequestType,
  requesting_department: '',
  clinical_head: '',
  device_model_ref: '',
  quantity: 1,
  target_year: currentYear + 1,
  clinical_justification: '',
  replacement_for_asset: '',
  utilization_pct_12m: undefined,
  downtime_hr_12m: undefined,
})

const canSubmit = computed(() =>
  form.request_type
  && form.requesting_department
  && form.clinical_head
  && form.device_model_ref
  && (form.quantity || 0) >= 1
  && (form.target_year || 0) >= currentYear
  && (form.clinical_justification || '').length >= 200,
)

async function onSubmit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const res = await store.create(form)
    router.push({ name: 'NeedsRequestDetail', params: { id: res.name } })
  } catch {
    /* error đã set trong store */
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.needs-request-create { padding: 1.5rem; max-width: 1100px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
.card h3 { margin: 0 0 1rem; color: #111827; }
.form label { display: block; margin-bottom: 0.75rem; font-weight: 500; }
.form input, .form select, .form textarea {
  display: block; width: 100%; padding: 0.55rem; border: 1px solid #d1d5db; border-radius: 6px;
  margin-top: 0.25rem; font-family: inherit; font-size: 0.95rem;
}
.form textarea { resize: vertical; min-height: 100px; }
.req { color: #ef4444; }
.hint { font-size: 0.8rem; color: #6b7280; margin-top: 0.2rem; display: block; }
.char-count { font-size: 0.85rem; color: #6b7280; }
.error-text { color: #b91c1c; margin-left: 0.5rem; }
.success-text { color: #065f46; margin-left: 0.5rem; }
.action-bar { display: flex; justify-content: flex-end; padding-top: 1rem; gap: 0.5rem; }
.alert { background: #fef2f2; border: 1px solid #fca5a5; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.alert-close { background: none; border: none; cursor: pointer; }
.btn { padding: 0.6rem 1.25rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; font-size: 0.9rem; }
.btn-primary { background: #2563eb; color: white; border-color: #2563eb; }
.btn-primary:disabled { background: #9ca3af; border-color: #9ca3af; cursor: not-allowed; }
.btn-outline { background: white; color: #2563eb; border-color: #2563eb; }
</style>
