<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm06Store } from '@/stores/imm06'
import { useAuthStore } from '@/stores/auth'
import { useApi } from '@/composables/useApi'
import { ROLES_TRAINING_MANAGE } from '@/constants/roles'
import type { TrainingProgram } from '@/api/imm06'
import StatusBadge from '@/components/common/StatusBadge.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const props = defineProps<{ name?: string }>()
const router = useRouter()
const store = useImm06Store()
const authStore = useAuthStore()
const api = useApi()

const { currentProgram, loading, error } = storeToRefs(store)

const isCreateMode = computed(() => !props.name)
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

const canManage = computed(() => authStore.hasAnyRole(ROLES_TRAINING_MANAGE))

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
  <div class="page-container animate-fade-in space-y-5">
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
    >
      <template #actions>
        <StatusBadge v-if="currentProgram && !isCreateMode" :state="currentProgram.is_active ? 'Active' : 'Inactive'" size="md" />
        <template v-if="canManage && !editing && !isCreateMode">
          <button class="btn-ghost text-sm" @click="startEdit">Chỉnh sửa</button>
        </template>
        <template v-if="editing || isCreateMode">
          <button v-if="!isCreateMode" class="btn-ghost text-sm" @click="cancelEdit">Hủy</button>
          <button class="btn-primary text-sm" :disabled="api.loading.value" @click="save">
            {{ api.loading.value ? 'Đang lưu…' : (isCreateMode ? 'Tạo chương trình' : 'Lưu thay đổi') }}
          </button>
        </template>
      </template>
    </PageHeader>

    <div v-if="loading" class="card p-8 text-center text-slate-400">Đang tải…</div>

    <div v-else-if="error && !isCreateMode" class="card border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3">
      <span class="flex-1">{{ error }}</span>
      <button class="text-sm underline" @click="load()">Thử lại</button>
    </div>

    <template v-else-if="currentProgram || isCreateMode">
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
            <p class="text-xs text-slate-400 mb-1">Tài liệu QMS</p>
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
            <label class="form-label">Mã chương trình <span class="text-red-500">*</span></label>
            <input v-model="form.program_code" type="text" class="form-input w-full" placeholder="VD: TRAIN-PB980-INIT" :readonly="!isCreateMode" />
          </div>
          <div>
            <label class="form-label">Tên chương trình <span class="text-red-500">*</span></label>
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
            <input v-model="form.target_device_model" type="text" class="form-input w-full" placeholder="Mã Device Model..." />
          </div>
          <div>
            <label class="form-label">Danh mục thiết bị</label>
            <input v-model="form.target_device_category" type="text" class="form-input w-full" />
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
            <label class="form-label">Tài liệu QMS</label>
            <input v-model="form.qms_doc_ref" type="text" class="form-input w-full" />
          </div>
          <div class="sm:col-span-2">
            <label class="form-label">Yêu cầu giảng viên</label>
            <input v-model="form.instructor_qualification_required" type="text" class="form-input w-full" />
          </div>
        </div>
      </div>

      <!-- Content outline -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-3 pb-2 border-b">Đề cương nội dung <span v-if="isCreateMode || editing" class="text-red-500">*</span></h2>
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

    <div v-else class="card p-8 text-center text-slate-400">Không tìm thấy chương trình.</div>
  </div>
</template>
