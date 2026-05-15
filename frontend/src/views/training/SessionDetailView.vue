<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm06Store } from '@/stores/imm06'
import { useAuthStore } from '@/stores/auth'
import { useApi } from '@/composables/useApi'
import { ROLES_TRAINING_MANAGE, ROLES_TRAINING_CONDUCT } from '@/constants/roles'
import { confirmSession, startSession, completeSession, cancelSession, verifySession, closeSession, createSession, enrollParticipants, removeParticipant } from '@/api/imm06'
import type { TrainingParticipant } from '@/api/imm06'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'


const props = defineProps<{ name?: string }>()
const router = useRouter()
const route = useRoute()
const store = useImm06Store()
const authStore = useAuthStore()
const api = useApi()

const { currentSession, loading, error } = storeToRefs(store)

const isCreateMode = computed(() => !props.name)

// Create form state
const createForm = ref({
  training_program: (route.query.program as string) ?? '',
  session_date: '',
  session_type: 'Onsite',
  location: '',
  instructor: '',
  instructor_external_name: '',
  evaluation_method: 'Cả hai' as 'Lý thuyết' | 'Thực hành' | 'Cả hai',
  trainer_ref: '',
  duration_planned_hours: 8,
})

const showCancelModal = ref(false)
const cancelReason = ref('')

// ── Enroll participants ──
const showEnroll = ref(false)
const enrollUser = ref('')
const enrollDepartment = ref('')
const enrolling = ref(false)

async function doEnroll() {
  if (!enrollUser.value || !props.name) return
  enrolling.value = true
  const result = await api.run(
    () => enrollParticipants(props.name!, [{ user: enrollUser.value, department: enrollDepartment.value || null }]),
    { successMessage: 'Đã thêm học viên' },
  )
  enrolling.value = false
  if (result) {
    enrollUser.value = ''
    enrollDepartment.value = ''
    showEnroll.value = false
    await store.fetchSession(props.name!)
  }
}

async function doRemoveParticipant(p: TrainingParticipant) {
  if (!p.name || !props.name) return
  const result = await api.run(
    () => removeParticipant(props.name!, p.name!),
    { successMessage: 'Đã xóa học viên' },
  )
  if (result) await store.fetchSession(props.name!)
}

const canManage = computed(() => authStore.hasAnyRole(ROLES_TRAINING_MANAGE))
const canConduct = computed(() => authStore.hasAnyRole(ROLES_TRAINING_CONDUCT))

const state = computed(() => currentSession.value?.workflow_state ?? '')

const canConfirm = computed(() => state.value === 'Planned' && canManage.value)
const canStart = computed(() => state.value === 'Confirmed' && canConduct.value)
const canComplete = computed(() => state.value === 'In Progress' && canConduct.value)
const canVerify = computed(() => state.value === 'Completed' && canManage.value)
const canClose = computed(() => state.value === 'Verified' && canManage.value)
const canCancel = computed(() => (state.value === 'Planned' || state.value === 'Confirmed') && canManage.value)

function resultClass(result: string | null) {
  if (!result) return 'text-slate-400'
  if (result === 'Pass') return 'text-emerald-600 font-semibold'
  if (result === 'Fail') return 'text-red-600 font-semibold'
  return 'text-amber-600 font-semibold'
}

function resultLabel(result: string | null) {
  if (!result) return '—'
  const map: Record<string, string> = { Pass: 'Đạt', Fail: 'Không đạt', Conditional: 'Có điều kiện' }
  return map[result] ?? result
}

async function doConfirm() {
  const result = await api.run(
    () => confirmSession(props.name!),
    { successMessage: 'Đã xác nhận buổi đào tạo' },
  )
  if (result) await store.fetchSession(props.name!)
}

async function doStart() {
  const result = await api.run(
    () => startSession(props.name!),
    { successMessage: 'Đã bắt đầu buổi đào tạo' },
  )
  if (result) await store.fetchSession(props.name!)
}

const isScoring = computed(() => state.value === 'In Progress' && canConduct.value)

async function doComplete() {
  const participants = (currentSession.value?.participants ?? []) as TrainingParticipant[]
  const result = await api.run(
    () => completeSession(props.name!, participants),
    { successMessage: 'Đã hoàn thành buổi đào tạo' },
  )
  if (result) await store.fetchSession(props.name!)
}

async function doVerify() {
  const result = await api.run(
    () => verifySession(props.name!),
    { successMessage: 'Đã xác minh buổi đào tạo' },
  )
  if (result) await store.fetchSession(props.name!)
}

async function doClose() {
  const result = await api.run(
    () => closeSession(props.name!),
    { successMessage: 'Đã đóng buổi đào tạo' },
  )
  if (result) await store.fetchSession(props.name!)
}

async function doCancel() {
  if (!cancelReason.value.trim()) return
  const result = await api.run(
    () => cancelSession(props.name!, cancelReason.value),
    { successMessage: 'Đã hủy buổi đào tạo' },
  )
  if (result) {
    showCancelModal.value = false
    cancelReason.value = ''
    await store.fetchSession(props.name!)
  }
}

async function doCreate() {
  const result = await api.run(
    () => createSession(createForm.value as Record<string, unknown>),
    { successMessage: 'Đã tạo buổi đào tạo' },
  )
  if (result) router.push(`/imm06/sessions/${result.name}`)
}

async function load() {
  if (!isCreateMode.value) {
    await store.fetchSession(props.name!)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      :title="isCreateMode ? 'Tạo buổi đào tạo mới' : (props.name ?? '')"
      :subtitle="isCreateMode ? 'Khai báo buổi đào tạo mới' : 'Buổi đào tạo'"
      :back-to="'/imm06/sessions'"
      back-label="← Danh sách buổi"
      :breadcrumb="[
        { label: 'IMM-06 · Đào tạo & Năng lực', to: '/imm06/sessions' },
        { label: 'Buổi đào tạo', to: '/imm06/sessions' },
        { label: isCreateMode ? 'Tạo mới' : (props.name ?? '') },
      ]"
    >
      <template #actions>
        <StatusBadge v-if="currentSession" :state="currentSession.workflow_state" size="md" />

        <button
          v-if="canConfirm"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doConfirm"
        >
          Xác nhận
        </button>

        <button
          v-if="isCreateMode"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doCreate"
        >
          {{ api.loading.value ? 'Đang tạo…' : 'Tạo buổi đào tạo' }}
        </button>

        <button
          v-if="canStart"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doStart"
        >
          Bắt đầu
        </button>

        <button
          v-if="canComplete"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doComplete"
        >
          {{ api.loading.value ? 'Đang lưu…' : 'Hoàn thành' }}
        </button>

        <button
          v-if="canVerify"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doVerify"
        >
          Xác minh
        </button>

        <button
          v-if="canClose"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doClose"
        >
          Đóng buổi
        </button>

        <button
          v-if="canCancel"
          class="btn-ghost text-sm text-red-600 hover:bg-red-50"
          @click="showCancelModal = true"
        >
          Hủy buổi
        </button>
      </template>
    </PageHeader>

    <!-- Create Form -->
    <div v-if="isCreateMode" class="card p-6 space-y-4">
      <h2 class="text-sm font-semibold text-slate-700 pb-2 border-b">Thông tin buổi đào tạo</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
        <div>
          <label class="form-label">Chương trình đào tạo <span class="text-red-500">*</span></label>
          <input v-model="createForm.training_program" type="text" class="form-input w-full" placeholder="Mã chương trình..." />
        </div>
        <div>
          <label class="form-label">Ngày tổ chức <span class="text-red-500">*</span></label>
          <input v-model="createForm.session_date" type="date" class="form-input w-full" />
        </div>
        <div>
          <label class="form-label">Hình thức</label>
          <select v-model="createForm.session_type" class="form-select w-full">
            <option value="Onsite">Tại chỗ</option>
            <option value="Online">Trực tuyến</option>
            <option value="Hybrid">Kết hợp</option>
          </select>
        </div>
        <div>
          <label class="form-label">Địa điểm</label>
          <input v-model="createForm.location" type="text" class="form-input w-full" />
        </div>
        <div>
          <label class="form-label">Giảng viên nội bộ</label>
          <input v-model="createForm.instructor" type="text" class="form-input w-full" placeholder="Email người dùng..." />
        </div>
        <div>
          <label class="form-label">Giảng viên bên ngoài</label>
          <input v-model="createForm.instructor_external_name" type="text" class="form-input w-full" />
        </div>
        <div>
          <label class="form-label">Giảng viên (IMM Trainer)</label>
          <SmartSelect v-model="createForm.trainer_ref" doctype="IMM Trainer" placeholder="Chọn giảng viên..." />
        </div>
        <div>
          <label class="form-label">Phương pháp đánh giá</label>
          <select v-model="createForm.evaluation_method" class="form-select w-full">
            <option value="Lý thuyết">Lý thuyết</option>
            <option value="Thực hành">Thực hành</option>
            <option value="Cả hai">Cả hai</option>
          </select>
        </div>
        <div>
          <label class="form-label">Thời lượng dự kiến (giờ)</label>
          <input v-model.number="createForm.duration_planned_hours" type="number" min="0" step="0.5" class="form-input w-full" />
        </div>
      </div>
      <p class="text-xs text-slate-400">* Phải có ít nhất một trong hai giảng viên.</p>
    </div>

    <div v-else-if="loading" class="card p-8 text-center text-slate-400">Đang tải…</div>

    <div v-else-if="error" class="card border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3">
      <span class="flex-1">{{ error }}</span>
      <button class="text-sm underline" @click="load()">Thử lại</button>
    </div>

    <template v-else-if="currentSession">
      <!-- Session Info -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b">Thông tin buổi đào tạo</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-5 text-sm">
          <div>
            <p class="text-xs text-slate-400 mb-1">Chương trình</p>
            <p class="font-medium">{{ currentSession.training_program_name || currentSession.training_program }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày tổ chức</p>
            <p>{{ currentSession.session_date }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Hình thức</p>
            <p>{{
              currentSession.session_type === 'Onsite' ? 'Tại chỗ'
              : currentSession.session_type === 'Online' ? 'Trực tuyến'
              : 'Kết hợp'
            }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Địa điểm</p>
            <p>{{ currentSession.location || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Giảng viên nội bộ</p>
            <p>{{ currentSession.instructor_full_name || currentSession.instructor || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Giảng viên bên ngoài</p>
            <p>{{ currentSession.instructor_external_name || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Tổ chức giảng viên</p>
            <p>{{ currentSession.instructor_external_org || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Giảng viên (IMM Trainer)</p>
            <p>{{ currentSession.trainer_ref_name || currentSession.trainer_ref || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Phương pháp đánh giá</p>
            <p>{{ currentSession.evaluation_method || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Thời lượng dự kiến</p>
            <p>{{ currentSession.duration_planned_hours }}h</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Thời lượng thực tế</p>
            <p>{{ currentSession.duration_actual_hours != null ? `${currentSession.duration_actual_hours}h` : '—' }}</p>
          </div>
        </div>
      </div>

      <!-- Participants Table -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4 pb-2 border-b">
          <h2 class="text-sm font-semibold text-slate-700">
            Học viên
            <span class="ml-2 px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs">
              {{ currentSession.participants?.length ?? 0 }}
            </span>
          </h2>
          <button
            v-if="canManage"
            type="button"
            class="text-xs px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium"
            @click="showEnroll = !showEnroll"
          >
            {{ showEnroll ? 'Đóng' : '+ Thêm học viên' }}
          </button>
        </div>

        <div v-if="showEnroll" class="mb-4 p-3 rounded-lg border border-dashed border-blue-200 bg-blue-50/40">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
            <div>
              <label class="text-[11px] text-slate-500 mb-1 block">Học viên *</label>
              <SmartSelect v-model="enrollUser" doctype="User" placeholder="Chọn người dùng..." />
            </div>
            <div>
              <label class="text-[11px] text-slate-500 mb-1 block">Khoa/Phòng</label>
              <SmartSelect v-model="enrollDepartment" doctype="AC Department" placeholder="Chọn khoa/phòng..." />
            </div>
            <div>
              <button
                type="button"
                :disabled="!enrollUser || enrolling"
                class="w-full text-sm px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium"
                @click="doEnroll"
              >
                {{ enrolling ? 'Đang thêm...' : 'Thêm vào buổi đào tạo' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="!currentSession.participants?.length" class="text-sm text-slate-400 py-4 text-center">
          Chưa có học viên nào.
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100 text-sm">
            <thead>
              <tr>
                <th class="table-header">Người dùng</th>
                <th class="table-header">Khoa/Phòng</th>
                <th class="table-header">Vai trò</th>
                <th class="table-header text-right">Điểm chuyên cần (%)</th>
                <th class="table-header text-right">Điểm LT</th>
                <th class="table-header text-right">Điểm TH</th>
                <th class="table-header">Kết quả</th>
                <th class="table-header">Cần thi lại</th>
                <th v-if="canManage" class="table-header text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="p in currentSession.participants" :key="p.user">
                <td class="table-cell font-medium">{{ p.user_full_name || p.user }}</td>
                <td class="table-cell text-slate-500">{{ p.department_name || p.department || '—' }}</td>
                <td class="table-cell text-slate-500">{{ p.role_at_session || '—' }}</td>
                <td class="table-cell text-right">
                  <input v-if="isScoring" v-model.number="p.attendance_pct" type="number" min="0" max="100" class="form-input w-20 text-right text-sm" />
                  <span v-else>{{ p.attendance_pct ?? '—' }}</span>
                </td>
                <td class="table-cell text-right">
                  <input v-if="isScoring" v-model.number="p.theory_score" type="number" min="0" max="100" class="form-input w-20 text-right text-sm" />
                  <span v-else>{{ p.theory_score ?? '—' }}</span>
                </td>
                <td class="table-cell text-right">
                  <input v-if="isScoring" v-model.number="p.practical_score" type="number" min="0" max="100" class="form-input w-20 text-right text-sm" />
                  <span v-else>{{ p.practical_score ?? '—' }}</span>
                </td>
                <td class="table-cell">
                  <span :class="resultClass(p.overall_result)">{{ resultLabel(p.overall_result) }}</span>
                </td>
                <td class="table-cell">
                  <span v-if="p.retake_required" class="text-xs text-amber-600 font-medium">Có</span>
                  <span v-else class="text-slate-300">—</span>
                </td>
                <td v-if="canManage" class="table-cell text-right">
                  <button
                    type="button"
                    class="text-red-500 hover:text-red-700 text-xs font-medium"
                    title="Xóa học viên"
                    @click="doRemoveParticipant(p)"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="card p-8 text-center text-slate-400">Không tìm thấy buổi đào tạo.</div>

    <!-- Cancel Modal -->
    <div v-if="showCancelModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Hủy buổi đào tạo</h2>
        <div>
          <label class="block text-sm font-medium mb-1">Lý do hủy <span class="text-red-500">*</span></label>
          <textarea
            v-model="cancelReason"
            rows="3"
            class="form-input w-full text-sm"
            placeholder="Nhập lý do hủy buổi đào tạo…"
          ></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50" @click="showCancelModal = false; cancelReason = ''">Quay lại</button>
          <button
            :disabled="api.loading.value || !cancelReason.trim()"
            class="px-4 py-2 text-sm bg-neutral-600 text-white rounded-lg hover:bg-neutral-700 disabled:opacity-50 transition-colors"
            @click="doCancel"
          >
            {{ api.loading.value ? 'Đang hủy…' : 'Xác nhận hủy' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
