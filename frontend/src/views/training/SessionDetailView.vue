<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm06Store } from '@/stores/imm06'
import { useCapabilities } from '@/composables/useCapabilities'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { confirmSession, startSession, completeSession, cancelSession, verifySession, closeSession, createSession, enrollParticipants, removeParticipant } from '@/api/imm06'
import type { TrainingParticipant } from '@/api/imm06'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import DateInput from '@/components/common/DateInput.vue'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import DetailLoadError from '@/components/common/DetailLoadError.vue'
import { loadErrorKind, type DetailLoadKind } from '@/api/errors'


const props = defineProps<{ name?: string }>()
const router = useRouter()
const route = useRoute()
const store = useImm06Store()
const { can } = useCapabilities()
const api = useApi()
const toast = useToast()

const { currentSession, loading, error, lastApiError } = storeToRefs(store)

const isCreateMode = computed(() => !props.name)

// Mã buổi đào tạo sai / đã xoá ⇒ 404: empty-state "không tìm thấy" + lối về danh
// sách (thay banner đỏ + "Thử lại" và dòng chữ cụt cuối template — dead-end).
const loadFailed = computed<'' | DetailLoadKind>(() => {
  if (isCreateMode.value || currentSession.value) return ''
  if (error.value) return loadErrorKind(lastApiError.value ?? new Error(error.value))
  return 'notfound'
})

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

// BUG-006: Gate UI bằng capability — BE rbac.require gate ở api/imm06.py.
// `training.submit` = Training Manager (confirm/verify/close/cancel session).
// `training.write` = Training User+Manager (conduct: start/complete + enroll).
const canManage = computed(() => can('training.submit'))
const canConduct = computed(() => can('training.write'))

const state = computed(() => currentSession.value?.workflow_state ?? '')

// GATE-8 / LL-FE-51: 6 CTA workflow gate theo SSoT server-driven `allowed_transitions`
// (BE _SESSION_VALID_TRANSITIONS, services/imm06.py) — KHÔNG hardcode state === 'X'.
// Capability (canManage/canConduct) enforce SONG SONG với state-machine.
// Desync fix: 'Bắt đầu' gate bằng includes('In Progress') → hiện cả khi buổi ở
// 'Planned' (BE start_training_session cho phép Planned→In Progress), không chỉ Confirmed.
const allowedTransitions = computed<string[]>(() => currentSession.value?.allowed_transitions ?? [])

const canConfirm = computed(() => allowedTransitions.value.includes('Confirmed') && canManage.value)
const canStart = computed(() => allowedTransitions.value.includes('In Progress') && canConduct.value)
const canComplete = computed(() => allowedTransitions.value.includes('Completed') && canConduct.value)
const canVerify = computed(() => allowedTransitions.value.includes('Verified') && canManage.value)
const canClose = computed(() => allowedTransitions.value.includes('Closed') && canManage.value)
const canCancel = computed(() => allowedTransitions.value.includes('Cancelled') && canManage.value)

// BUG-006: Hint nếu user xem session ở state cần thao tác nhưng không có quyền nào.
const hasAnyAction = computed(() =>
  canConfirm.value || canStart.value || canComplete.value ||
  canVerify.value || canClose.value || canCancel.value,
)
const isTerminalState = computed(() =>
  ['Closed', 'Cancelled'].includes(state.value),
)
const showPermissionHint = computed(() =>
  !!currentSession.value && !isTerminalState.value && !hasAnyAction.value,
)

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

// BR-06-08 (chống nghiệm-thu-giả) — DIRTY-TRACKING, KHÔNG suy từ giá trị:
// get_session trả theory_score/practical_score = 0 (child DocType Float ⇒ DB NOT NULL
// DEFAULT 0) cho học viên CHƯA chấm. 0 vừa là default-lưu-trữ vừa là điểm-hợp-lệ ⇒ KHÔNG
// thể phân biệt "chưa chấm" với "chấm 0" bằng giá trị. Vì vậy "đã chấm" = instructor THỰC
// SỰ gõ vào ô điểm lý thuyết/thực hành TRONG phiên này (markScored theo @input). Chuyên
// cần (attendance_pct) KHÔNG tính là chấm điểm. Key theo p.user để khớp result_map BE
// (complete_training_session map theo r["user"]).
const scoredKeys = ref<Set<string>>(new Set())
function markScored(p: TrainingParticipant) {
  if (p.user) scoredKeys.value.add(p.user)
}
const scoredParticipants = computed<TrainingParticipant[]>(() =>
  ((currentSession.value?.participants ?? []) as TrainingParticipant[]).filter(
    (p) => !!p.user && scoredKeys.value.has(p.user),
  ),
)
// Gate nút "Hoàn thành": phải chấm điểm ≥1 học viên trước khi hoàn thành buổi (BR-06-08).
const hasAnyScore = computed(() => scoredParticipants.value.length > 0)

async function doComplete() {
  // Guard kép: nút đã disabled khi chưa chấm ai; chặn luôn ở handler (double-safety,
  // tránh trigger qua phím/enter khi 0 điểm → BE cũng raise VALIDATION BR-06-08).
  if (!hasAnyScore.value) return
  // Chỉ gửi học viên ĐÃ được chấm → BE set overall_result đúng tập này (partial-scoring),
  // scored_count đếm THỰC trong loop, không kéo theo học viên chưa chấm.
  const result = await api.run(
    () => completeSession(props.name!, scoredParticipants.value),
    // silentSuccess: dựng toast từ kết quả THỰC của BE (scored_count/competencies_created),
    // KHÔNG dùng chuỗi tĩnh / số dòng local (anti success-giả). Reject-path (VALIDATION…)
    // vẫn được api.run surface qua notify.fromError → không toast success, không điều hướng.
    { silentSuccess: true },
  )
  if (result) {
    const scored = typeof result.scored_count === 'number'
      ? result.scored_count
      : scoredParticipants.value.length
    const certs = result.competencies_created?.length ?? 0
    toast.success(
      `Đã hoàn thành buổi đào tạo — đã chấm điểm ${scored} học viên, cấp ${certs} chứng nhận năng lực.`,
    )
    await store.fetchSession(props.name!)
  }
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
  // Reset dirty-tracking khi (re)load buổi khác → không kéo cờ "đã chấm" phiên trước.
  scoredKeys.value = new Set()
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
          data-testid="cta-confirm"
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
          data-testid="cta-start"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doStart"
        >
          Bắt đầu
        </button>

        <button
          v-if="canComplete"
          data-testid="cta-complete"
          class="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="api.loading.value || !hasAnyScore"
          :title="!hasAnyScore ? 'Chưa chấm điểm học viên nào' : undefined"
          :aria-describedby="!hasAnyScore ? 'complete-score-hint' : undefined"
          @click="doComplete"
        >
          {{ api.loading.value ? 'Đang lưu…' : 'Hoàn thành' }}
        </button>

        <button
          v-if="canVerify"
          data-testid="cta-verify"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doVerify"
        >
          Xác minh
        </button>

        <button
          v-if="canClose"
          data-testid="cta-close"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doClose"
        >
          Đóng buổi
        </button>

        <button
          v-if="canCancel"
          data-testid="cta-cancel"
          class="btn-ghost text-sm text-red-600 hover:bg-red-50"
          @click="showCancelModal = true"
        >
          Hủy buổi
        </button>
      </template>
    </PageHeader>

    <!-- BUG-006: Permission hint khi user không có quyền hành động trên buổi -->
    <div
      v-if="!isCreateMode && showPermissionHint"
      class="card p-4 bg-amber-50 border-amber-200 text-sm text-amber-800 flex items-start gap-3"
    >
      <svg class="w-5 h-5 shrink-0 text-amber-500 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
      </svg>
      <div>
        <p class="font-medium">Bạn không có quyền thực hiện hành động trên buổi đào tạo này.</p>
        <p class="text-xs mt-0.5">Liên hệ quản trị để cấp vai trò Training User (giảng dạy) hoặc Training Manager (duyệt/đóng).</p>
      </div>
    </div>

    <!-- BR-06-08: buổi đang diễn ra + có quyền hoàn thành nhưng chưa chấm điểm ai -->
    <div
      v-if="!isCreateMode && canComplete && !hasAnyScore"
      id="complete-score-hint"
      data-testid="complete-score-hint"
      role="status"
      class="card p-4 bg-slate-50 border-slate-200 text-sm text-slate-600 flex items-start gap-3"
    >
      <svg class="w-5 h-5 shrink-0 text-slate-400 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
      </svg>
      <div>
        <p class="font-medium text-slate-700">Chưa chấm điểm học viên nào.</p>
        <p class="text-xs mt-0.5">Nhập điểm lý thuyết hoặc thực hành cho ít nhất một học viên trước khi hoàn thành buổi học.</p>
      </div>
    </div>

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
          <DateInput v-model="createForm.session_date" class="form-input w-full" />
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
          <ApproverSelect v-model="createForm.instructor" context="user" placeholder="Chọn giảng viên..." />
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

    <DetailLoadError
      v-else-if="loadFailed"
      :kind="loadFailed"
      entity-label="buổi đào tạo"
      :record-id="props.name"
      :message="error ?? ''"
      back-label="Về danh sách buổi đào tạo"
      @retry="load()"
      @back="router.push('/imm06/sessions')"
    />

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
              <ApproverSelect v-model="enrollUser" context="user" placeholder="Chọn người dùng..." />
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
                <th class="table-header text-right">Điểm lý thuyết</th>
                <th class="table-header text-right">Điểm thực hành</th>
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
                  <input v-if="isScoring" v-model.number="p.theory_score" :data-testid="`theory-score-${p.user}`" @input="markScored(p)" type="number" min="0" max="100" class="form-input w-20 text-right text-sm" />
                  <span v-else>{{ p.theory_score ?? '—' }}</span>
                </td>
                <td class="table-cell text-right">
                  <input v-if="isScoring" v-model.number="p.practical_score" :data-testid="`practical-score-${p.user}`" @input="markScored(p)" type="number" min="0" max="100" class="form-input w-20 text-right text-sm" />
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
