<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useImm01Store } from '@/stores/imm01'
import { frappeGet } from '@/api/helpers'
import SmartSelect from '@/components/common/SmartSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import type { NeedsRequestDoc, RequestType } from '@/types/imm01'

const router = useRouter()
const store = useImm01Store()

const currentYear = new Date().getFullYear()
const submitting = ref(false)
const headLoading = ref(false)
const clinicalHeadName = ref('')

const form = reactive<Partial<NeedsRequestDoc>>({
  request_type: 'New' as RequestType,
  requesting_department: '',
  clinical_head: '',
  device_category: '',
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
  && form.device_category
  && (form.quantity || 0) >= 1
  && (form.target_year || 0) >= currentYear
  && (form.clinical_justification || '').length > 0
  && (form.request_type !== 'Replacement' || !!form.replacement_for_asset),
)

// Cascade: đổi danh mục → reset model đã chọn
function onCategoryChange() {
  form.device_model_ref = ''
}

async function onDepartmentSelected(item: { id: string }) {
  if (!item?.id) { resetClinicalHead(); return }
  headLoading.value = true
  form.clinical_head = ''
  clinicalHeadName.value = ''
  try {
    const dept = await frappeGet<{ dept_head?: string }>('/api/method/frappe.client.get_value', {
      doctype: 'AC Department',
      filters: item.id,
      fieldname: JSON.stringify(['dept_head']),
    })
    if (dept?.dept_head) {
      form.clinical_head = dept.dept_head
      const user = await frappeGet<{ full_name?: string }>('/api/method/frappe.client.get_value', {
        doctype: 'User',
        filters: dept.dept_head,
        fieldname: JSON.stringify(['full_name']),
      })
      clinicalHeadName.value = user?.full_name || dept.dept_head
    }
  } catch {
    resetClinicalHead()
  } finally {
    headLoading.value = false
  }
}

function onDepartmentCleared() { resetClinicalHead() }
function resetClinicalHead() { form.clinical_head = ''; clinicalHeadName.value = '' }

async function onSubmit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    const { clinical_head: _ch, ...payload } = form
    void _ch
    const res = await store.create(payload)
    router.push({ name: 'NeedsRequestDetail', params: { id: res.name } })
  } catch {
    /* error đã set trong store */
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-container animate-fade-in max-w-[1100px] mx-auto">
    <PageHeader
      title="Tạo đề xuất nhu cầu thiết bị"
      subtitle="Khai báo thông tin cơ bản, thiết bị muốn mua và lý do lâm sàng."
      :back-to="{ name: 'NeedsRequestList' }"
    />

    <div v-if="store.error" class="alert-error mb-4">
      <span><strong>Lỗi:</strong> {{ store.error }}</span>
      <button class="text-red-700 text-lg leading-none" @click="store.clearError()">×</button>
    </div>

    <form class="space-y-4 animate-slide-up" @submit.prevent="onSubmit">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section class="card">
          <div class="section-title">1 · Thông tin cơ bản</div>
          <div class="space-y-4">
            <div class="form-group">
              <label class="form-label">Loại đề xuất <span class="text-red-500">*</span></label>
              <select v-model="form.request_type" required class="form-select">
                <option value="New">Mua mới</option>
                <option value="Replacement">Thay thế</option>
                <option value="Upgrade">Nâng cấp</option>
                <option value="Add-on">Bổ sung</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Khoa đề xuất <span class="text-red-500">*</span></label>
              <SmartSelect
                v-model="form.requesting_department"
                doctype="AC Department"
                placeholder="Tìm khoa theo tên hoặc mã..."
                @select="onDepartmentSelected"
                @clear="onDepartmentCleared"
              />
              <p class="text-xs text-slate-500 mt-1">Khoa lâm sàng đề nghị mua sắm thiết bị</p>
            </div>
            <div class="form-group">
              <label class="form-label">Trưởng khoa</label>
              <div class="readonly-field" :class="{ empty: !clinicalHeadName }">
                <span v-if="headLoading">Đang tải...</span>
                <span v-else-if="clinicalHeadName">
                  {{ clinicalHeadName }}
                  <span class="font-mono text-xs text-slate-500 ml-1">({{ form.clinical_head }})</span>
                </span>
                <span v-else-if="form.requesting_department" class="text-slate-400 italic">
                  Khoa này chưa khai báo Trưởng khoa
                </span>
                <span v-else class="text-slate-400 italic">Chọn khoa đề xuất để tự điền</span>
              </div>
              <p class="text-xs text-slate-500 mt-1">Trưởng khoa lấy tự động từ "Khoa đề xuất" — không thể chỉnh tay.</p>
            </div>
          </div>
        </section>

        <section class="card">
          <div class="section-title">2 · Thiết bị muốn mua</div>
          <div class="space-y-4">
            <div class="form-group">
              <label class="form-label">Danh mục thiết bị <span class="text-red-500">*</span></label>
              <SmartSelect
                v-model="form.device_category"
                doctype="AC Asset Category"
                placeholder="Tìm danh mục thiết bị..."
                @select="onCategoryChange"
                @clear="onCategoryChange"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Mẫu thiết bị <span class="text-xs text-slate-400 normal-case">(tùy chọn)</span></label>
              <SmartSelect
                v-model="form.device_model_ref"
                doctype="IMM Device Model"
                :filters="{ asset_category: form.device_category }"
                placeholder="Tìm mẫu thiết bị..."
              />
            </div>
            <div class="form-group">
              <label class="form-label">Số lượng <span class="text-red-500">*</span></label>
              <input v-model.number="form.quantity" type="number" min="1" required class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">Năm dự kiến mua <span class="text-red-500">*</span></label>
              <input v-model.number="form.target_year" type="number" :min="currentYear" required class="form-input" />
              <p class="text-xs text-slate-500 mt-1">Phải từ năm {{ currentYear }} trở đi</p>
            </div>
            <div v-if="form.request_type === 'Replacement'" class="form-group">
              <label class="form-label">Thiết bị cần thay thế <span class="text-red-500">*</span></label>
              <SmartSelect
                v-model="form.replacement_for_asset"
                doctype="AC Asset"
                placeholder="Tìm thiết bị theo tên / mã / serial..."
              />
              <p class="text-xs text-slate-500 mt-1">Thiết bị thay thế phải có kế hoạch thanh lý đi kèm</p>
            </div>
          </div>
        </section>
      </div>

      <section class="card">
        <div class="section-title">3 · Lý do lâm sàng <span class="text-red-500 normal-case">*</span></div>
        <textarea
          v-model="form.clinical_justification" rows="6" required
          class="form-textarea"
          placeholder="Mô tả nhu cầu lâm sàng, ảnh hưởng nếu không có thiết bị..."
        />
      </section>

      <section v-if="form.request_type === 'Replacement' || form.request_type === 'Upgrade'" class="card">
        <div class="section-title">4 · Dữ liệu sử dụng 12 tháng gần nhất</div>
        <p class="text-xs text-slate-500 mb-3">
          Bắt buộc với đề xuất thay thế / nâng cấp để hệ thống chấm điểm tín hiệu cần thay thế.
        </p>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="form-group">
            <label class="form-label">Tỷ lệ sử dụng (%)</label>
            <input v-model.number="form.utilization_pct_12m" type="number" step="0.01" min="0" max="100" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Thời gian ngừng hoạt động (giờ)</label>
            <input v-model.number="form.downtime_hr_12m" type="number" step="0.1" min="0" class="form-input" />
          </div>
        </div>
      </section>

      <div class="flex justify-end gap-2 pt-2">
        <button type="button" class="btn-secondary" @click="router.push({ name: 'NeedsRequestList' })">Huỷ</button>
        <button type="submit" class="btn-primary" :disabled="!canSubmit || submitting">
          {{ submitting ? 'Đang lưu...' : 'Tạo bản nháp' }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.readonly-field {
  display: block; padding: 0.55rem 0.75rem;
  border: 1px dashed #cbd5e1; border-radius: 8px;
  background: #f8fafc; font-size: 0.9375rem; color: #0f172a; min-height: 2.5rem;
}
.readonly-field.empty { color: #64748b; }
</style>

<style>
.alert-error {
  display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
  background: #fef2f2; border: 1px solid #fecaca; padding: 0.75rem 1rem;
  border-radius: 8px; color: #b91c1c; font-size: 0.875rem;
}
</style>
