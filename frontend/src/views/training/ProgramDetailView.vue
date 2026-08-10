<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm06Store } from '@/stores/imm06'
import { useApi } from '@/composables/useApi'
import { useCapabilities } from '@/composables/useCapabilities'
import type { TrainingProgram } from '@/api/imm06'
import StatusBadge from '@/components/common/StatusBadge.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'

const props = defineProps<{ name?: string }>()
const router = useRouter()
const store = useImm06Store()
const api = useApi()
const { can } = useCapabilities()

const { currentProgram, loading, error, lastApiError } = storeToRefs(store)

// Màn LƯỠNG DỤNG tạo/sửa (§13.4.3): router trỏ CÙNG view cho `/imm06/programs/new` và
// `/imm06/programs/:name`. Nối shell theo lối ngây thơ ⇒ ở chế độ tạo `doc` rỗng ⇒ shell rơi
// vào `notfound` và BIỂU MẪU TẠO BIẾN MẤT. Vì vậy 4 prop `loading`/`error-kind`/`doc`/`not-found`
// đều rẽ theo `isCreateMode`, và `:doc` nhận `form` (luôn có) khi đang tạo.
const isCreateMode = computed(() => !props.name)

// SSoT phân loại lỗi nạp (AC-UX-053, ADR-UX-27) — thay bản `loadErrorKind` cục bộ.
// Chế độ TẠO MỚI không có lượt nạp nào ⇒ không bao giờ có lỗi nạp (§13.4.3).
const { kind: loadKind, message: loadMsg } = useDetailAccess(() =>
  isCreateMode.value || currentProgram.value
    ? null
    // `?.` KHÔNG thừa: nhiều test cũ mock `useImm06Store` KHÔNG khai `lastApiError`/`error`,
    // `storeToRefs` khi đó trả `undefined` và computed này chạy cả sau khi component unmount
    // (flushJobs) ⇒ unhandled rejection làm bẩn cả suite dù test vẫn xanh.
    : (lastApiError?.value ?? (error?.value ? new Error(error.value) : null)),
)
const editing = ref(false)
const form = ref<Partial<TrainingProgram>>({
  training_type: 'Initial',
  assessment_method: 'Both',
  duration_hours: 8,
  validity_period_months: 12,
  passing_score_pct: 70,
  is_mandatory_for_operation: 0,
  is_active: 1,
  content_outline: '',
})

const canManage = computed(() => can('training.write'))

const TRAINING_TYPES = [
  { value: 'Initial',       label: 'Đào tạo ban đầu' },
  { value: 'Refresher',     label: 'Đào tạo nhắc lại' },
  { value: 'Advanced',      label: 'Đào tạo nâng cao' },
  { value: 'Certification', label: 'Chứng nhận' },
]

const ASSESSMENT_METHODS = [
  { value: 'Theory',    label: 'Lý thuyết' },
  { value: 'Practical', label: 'Thực hành' },
  { value: 'Both',      label: 'Cả hai' },
]

function typeLabel(v: string) {
  return TRAINING_TYPES.find(t => t.value === v)?.label ?? v
}

function methodLabel(v: string) {
  return ASSESSMENT_METHODS.find(m => m.value === v)?.label ?? v
}

function startEdit() {
  form.value = { ...currentProgram.value }
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  form.value = {}
}

async function save() {
  if (isCreateMode.value) {
    const newName = await store.doCreateProgram(form.value)
    if (newName) router.push(`/imm06/programs/${newName}`)
  } else {
    await api.run(
      () => store.doUpdateProgram(props.name!, form.value),
      { successMessage: 'Đã cập nhật chương trình đào tạo' },
    )
    editing.value = false
  }
}

async function load() {
  if (!isCreateMode.value) {
    await store.fetchProgram(props.name!)
  } else {
    // create mode: start in editing state with blank form
    editing.value = true
  }
}

onMounted(load)
</script>

<template>
  <DetailPageShell
    :loading="isCreateMode ? false : loading"
    :error-kind="isCreateMode ? '' : loadKind"
    :error-message="isCreateMode ? '' : loadMsg"
    :doc="isCreateMode ? form : currentProgram"
    :not-found="!isCreateMode && !loading && !currentProgram"
    entity-label="chương trình đào tạo"
    :record-id="props.name"
    back-label="Về danh sách chương trình"
    @retry="load()"
    @back="router.push('/imm06/programs')">
    <template #title>
      <PageHeader
        :title="isCreateMode ? 'Tạo chương trình mới' : (currentProgram?.program_name ?? props.name ?? '')"
        :subtitle="isCreateMode ? 'Khai báo chương trình đào tạo mới' : 'Chương trình đào tạo'"
        :back-to="'/imm06/programs'"
        back-label="← Danh sách chương trình"
        :breadcrumb="[
          { label: 'IMM-06 · Đào tạo & Năng lực', to: '/imm06/programs' },
          { label: 'Chương trình', to: '/imm06/programs' },
          { label: isCreateMode ? 'Tạo mới' : (currentProgram?.program_name ?? props.name ?? '') },
        ]"
      />
    </template>

    <!-- CTA vòng đời — CHỈ tồn tại ở trạng thái content (AC-UX-053). -->
    <template #actions>
      <StatusBadge v-if="currentProgram && !isCreateMode" :state="currentProgram.is_active ? 'Active' : 'Inactive'" size="md" />
      <template v-if="canManage && !editing && !isCreateMode">
        <button class="btn-ghost text-sm" data-testid="cta-edit" @click="startEdit">Chỉnh sửa</button>
      </template>
      <template v-if="editing || isCreateMode">
        <button v-if="!isCreateMode" class="btn-ghost text-sm" data-testid="cta-cancel-edit" @click="cancelEdit">Hủy</button>
        <button class="btn-primary text-sm" data-testid="cta-save" :disabled="api.loading.value" @click="save">
          {{ api.loading.value ? 'Đang lưu…' : (isCreateMode ? 'Tạo chương trình' : 'Lưu thay đổi') }}
        </button>
      </template>
    </template>

    <template v-if="currentProgram || isCreateMode">
      <div v-if="error && isCreateMode" class="card border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 text-sm">{{ error }}</div>
      <!-- General Info -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b">Thông tin chung</h2>
        <div v-if="!editing && !isCreateMode" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 text-sm">
          <div>
            <p class="text-xs text-slate-400 mb-1">Mã chương trình</p>
            <p class="font-mono text-slate-600">{{ currentProgram?.name }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Loại đào tạo</p>
            <p>{{ typeLabel(currentProgram?.training_type ?? '') }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Phương pháp đánh giá</p>
            <p>{{ methodLabel(currentProgram?.assessment_method ?? '') }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Device Model mục tiêu</p>
            <p>{{ currentProgram?.target_device_model_name || currentProgram?.target_device_model || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Danh mục thiết bị</p>
            <p>{{ currentProgram?.target_device_category ?? '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Thời lượng</p>
            <p>{{ currentProgram?.duration_hours }} giờ</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Hiệu lực (tháng)</p>
            <p>{{ currentProgram?.validity_period_months }} tháng</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Điểm đạt</p>
            <p class="font-semibold text-emerald-600">{{ currentProgram?.passing_score_pct }}%</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Bắt buộc vận hành</p>
            <p>{{ currentProgram?.is_mandatory_for_operation ? 'Có' : 'Không' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Tài liệu hệ thống quản lý chất lượng</p>
            <p>{{ currentProgram?.qms_doc_ref ?? '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Cập nhật lần cuối</p>
            <p class="text-slate-500">{{ currentProgram?.modified?.slice(0, 10) }}</p>
          </div>
        </div>

        <!-- Edit / Create form -->
        <div v-if="editing || isCreateMode" class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <label class="form-label">Mã chương trình <span class="text-danger-500">*</span></label>
            <input v-model="form.program_code" type="text" class="form-input w-full" placeholder="VD: TRAIN-PB980-INIT" :readonly="!isCreateMode" />
            <p v-if="isCreateMode" class="text-xs text-slate-400 mt-1">
              Mã không đổi sau khi tạo. Gợi ý: <code>TRAIN-&lt;model&gt;-&lt;type&gt;</code> (VD: TRAIN-PB980-INIT).
            </p>
          </div>
          <div>
            <label class="form-label">Tên chương trình <span class="text-danger-500">*</span></label>
            <input v-model="form.program_name" type="text" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Loại đào tạo</label>
            <select v-model="form.training_type" class="form-select w-full">
              <option v-for="t in TRAINING_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="form-label">Device Model mục tiêu</label>
            <SmartSelect
              v-model="form.target_device_model"
              doctype="IMM Device Model"
              placeholder="Chọn Device Model..."
            />
          </div>
          <div>
            <label class="form-label">Danh mục thiết bị</label>
            <SmartSelect
              v-model="form.target_device_category"
              doctype="AC Asset Category"
              placeholder="Chọn danh mục..."
            />
          </div>
          <div>
            <label class="form-label">Thời lượng (giờ)</label>
            <input v-model.number="form.duration_hours" type="number" min="0" step="0.5" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Hiệu lực (tháng)</label>
            <input v-model.number="form.validity_period_months" type="number" min="1" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Điểm đạt (%)</label>
            <input v-model.number="form.passing_score_pct" type="number" min="0" max="100" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Phương pháp đánh giá</label>
            <select v-model="form.assessment_method" class="form-select w-full">
              <option v-for="m in ASSESSMENT_METHODS" :key="m.value" :value="m.value">{{ m.label }}</option>
            </select>
          </div>
          <div>
            <label class="form-label">Bắt buộc vận hành</label>
            <select v-model.number="form.is_mandatory_for_operation" class="form-select w-full">
              <option :value="0">Không</option>
              <option :value="1">Có</option>
            </select>
          </div>
          <div>
            <label class="form-label">Đang hoạt động</label>
            <select v-model.number="form.is_active" class="form-select w-full">
              <option :value="1">Có</option>
              <option :value="0">Không</option>
            </select>
          </div>
          <div>
            <label class="form-label">Tài liệu hệ thống quản lý chất lượng</label>
            <input
              v-model="form.qms_doc_ref"
              type="text"
              class="form-input w-full"
              placeholder="Mã Asset Document (VD: ADOC-2026-00012)"
            />
            <p class="text-xs text-slate-400 mt-1">Liên kết đến Asset Document. Để trống nếu chưa gắn.</p>
          </div>
          <div class="sm:col-span-2">
            <label class="form-label">Yêu cầu giảng viên</label>
            <input v-model="form.instructor_qualification_required" type="text" class="form-input w-full" />
          </div>
        </div>
      </div>

      <!-- Content outline -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b">Đề cương nội dung <span v-if="isCreateMode || editing" class="text-danger-500">*</span></h2>
        <div v-if="!editing && !isCreateMode">
          <p v-if="currentProgram?.content_outline" class="text-sm text-slate-700 whitespace-pre-line">{{ currentProgram.content_outline }}</p>
          <p v-else class="text-sm text-slate-400">Chưa có đề cương.</p>
        </div>
        <div v-else>
          <textarea v-model="form.content_outline" rows="6" class="form-input w-full text-sm" placeholder="Nội dung đề cương đào tạo..."></textarea>
        </div>
      </div>

      <!-- Instructor requirement (view only) -->
      <div v-if="!editing && !isCreateMode && currentProgram?.instructor_qualification_required" class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-2 pb-2 border-b">Yêu cầu giảng viên</h2>
        <p class="text-sm text-slate-700">{{ currentProgram.instructor_qualification_required }}</p>
      </div>
    </template>
  </DetailPageShell>
</template>
