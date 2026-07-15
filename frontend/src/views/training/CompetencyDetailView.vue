<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCapabilities } from '@/composables/useCapabilities'
import { useApi } from '@/composables/useApi'
import { getCompetency, signoffCompetency, revokeCompetency, recertifyCompetency, suspendCompetency, restoreCompetency } from '@/api/imm06'
import type { UserCompetency } from '@/api/imm06'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { competencyEffectiveState } from './competencyStatus'

const props = defineProps<{ name: string }>()
const { can } = useCapabilities()
const api = useApi()

const competency = ref<UserCompetency | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const showRevokeModal = ref(false)
const revokeReason = ref('')
const revokeCapa = ref('')

const showRecertModal = ref(false)
const recertSession = ref('')

const showSuspendModal = ref(false)
const suspendReason = ref('')

const showRestoreModal = ref(false)

// GATE-8 / LL-FE-51: server-driven CTA. Gate 3 nút vòng đời theo allowed_transitions
// (BE derive từ SSoT _COMPETENCY_VALID_TRANSITIONS đã enforce) + cờ capability đã lọc.
// KHÔNG hardcode workflow_state === 'X' và KHÔNG suy state client (degrade an toàn:
// allowed_transitions vắng → [] → 0 nút → no-actions-hint).
const allowedTransitions = computed<string[]>(() => competency.value?.allowed_transitions ?? [])

const canSignoff = computed(
  () => allowedTransitions.value.includes('Sign-off')
    && (competency.value?.can_signoff ?? can('training.submit')),
)
const canRevoke = computed(
  () => allowedTransitions.value.includes('Revoke')
    && (competency.value?.can_revoke ?? can('training.submit')),
)
const canRecertify = computed(
  () => allowedTransitions.value.includes('Recertify')
    && (competency.value?.can_recertify ?? can('training.submit')),
)
// CR-WF-06-COMP: Tạm ngưng (Active→Suspended) + Khôi phục (Suspended→Active).
// Gate THUẦN theo allowed_transitions (BE derive từ SSoT _COMPETENCY_VALID_TRANSITIONS:
// Active chứa 'Suspend'; Suspended == ['Restore','Revoke']) + cờ capability đã lọc.
// KHÔNG hardcode workflow_state === 'X' (GATE-8 / LL-FE-51).
const canSuspend = computed(
  () => allowedTransitions.value.includes('Suspend')
    && (competency.value?.can_suspend ?? can('training.submit')),
)
const canRestore = computed(
  () => allowedTransitions.value.includes('Restore')
    && (competency.value?.can_restore ?? can('training.submit')),
)

const hasAnyAction = computed(
  () => canSignoff.value || canRevoke.value || canRecertify.value
    || canSuspend.value || canRestore.value,
)
// State CÓ hành động khả dụng ở server (allowed_transitions non-empty) nhưng user
// không đủ quyền → hint "không đủ quyền". State không có action (terminal / vắng
// allowed_transitions) → hint "không có thao tác". Cả hai chỉ hiện khi hasAnyAction=false.
const hasServerActions = computed(() => allowedTransitions.value.length > 0)
const showPermissionHint = computed(() =>
  !!competency.value && hasServerActions.value && !hasAnyAction.value,
)
const showNoActionsHint = computed(() =>
  !!competency.value && !hasServerActions.value && !hasAnyAction.value,
)

// BUG-011: Hint cho điểm trống — giải thích scoring flow (set qua session complete).
const hasNoScores = computed(() =>
  !!competency.value &&
  competency.value.theory_score == null &&
  competency.value.practical_score == null &&
  competency.value.last_assessment_score == null,
)

function levelLabel(v: string): string {
  const map: Record<string, string> = {
    'Trainee':         'Học viên',
    'Operator':        'Vận hành viên',
    'Senior Operator': 'Vận hành viên cao cấp',
    'Trainer':         'Giảng viên',
  }
  return map[v] ?? v
}

function expiryClass(days: number | null): string {
  if (days === null) return 'text-slate-600'
  if (days < 0) return 'text-red-600 font-semibold'
  if (days < 30) return 'text-red-600 font-semibold'
  if (days < 60) return 'text-amber-600 font-semibold'
  return 'text-emerald-600'
}

function formatDays(days: number | null): string {
  if (days === null) return '—'
  if (days < 0) return `Đã hết hạn ${Math.abs(days)} ngày`
  if (days === 0) return 'Hết hạn hôm nay'
  return `Còn ${days} ngày`
}

async function load() {
  loading.value = true
  error.value = null
  try {
    // Server-driven: get_competency trả record + allowed_transitions + cờ capability.
    competency.value = await getCompetency(props.name)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
    competency.value = null
  } finally {
    loading.value = false
  }
}

async function doSignoff() {
  const result = await api.run(
    () => signoffCompetency(props.name),
    { successMessage: 'Đã phê duyệt năng lực' },
  )
  if (result) await load()
}

async function doRevoke() {
  if (!revokeReason.value.trim()) return
  const result = await api.run(
    () => revokeCompetency(props.name, revokeReason.value, revokeCapa.value || undefined),
    { successMessage: 'Đã thu hồi năng lực' },
  )
  if (result) {
    showRevokeModal.value = false
    revokeReason.value = ''
    revokeCapa.value = ''
    await load()
  }
}

async function doRecertify() {
  if (!recertSession.value.trim()) return
  const result = await api.run(
    () => recertifyCompetency(props.name, recertSession.value.trim()),
    { successMessage: 'Đã tái chứng nhận năng lực' },
  )
  if (result) {
    showRecertModal.value = false
    recertSession.value = ''
    await load()
  }
}

async function doSuspend() {
  if (!suspendReason.value.trim()) return
  const result = await api.run(
    () => suspendCompetency(props.name, suspendReason.value.trim()),
    { successMessage: 'Đã tạm ngưng năng lực' },
  )
  if (result) {
    showSuspendModal.value = false
    suspendReason.value = ''
    await load()
  }
}

async function doRestore() {
  const result = await api.run(
    () => restoreCompetency(props.name),
    { successMessage: 'Đã khôi phục năng lực' },
  )
  if (result) {
    showRestoreModal.value = false
    await load()
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      :title="competency?.user_full_name ?? props.name"
      :subtitle="`Năng lực · ${props.name}`"
      :back-to="'/imm06/competencies'"
      back-label="← Danh sách năng lực"
      :breadcrumb="[
        { label: 'IMM-06 · Đào tạo & Năng lực', to: '/imm06/competencies' },
        { label: 'Năng lực', to: '/imm06/competencies' },
        { label: props.name },
      ]"
    >
      <template #actions>
        <StatusBadge
          v-if="competency"
          :state="competencyEffectiveState(competency.workflow_state, competency.days_until_expiry)"
          size="md"
        />

        <button
          v-if="canSignoff"
          data-testid="cta-signoff"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="doSignoff"
        >
          Phê duyệt
        </button>

        <button
          v-if="canRecertify"
          data-testid="cta-recertify"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="showRecertModal = true"
        >
          Tái chứng nhận
        </button>

        <button
          v-if="canRestore"
          data-testid="cta-restore"
          class="btn-primary text-sm"
          :disabled="api.loading.value"
          @click="showRestoreModal = true"
        >
          Khôi phục
        </button>

        <button
          v-if="canSuspend"
          data-testid="cta-suspend"
          class="btn-ghost text-sm text-amber-600 hover:bg-amber-50 focus-visible:ring-2 focus-visible:ring-amber-500 rounded"
          @click="showSuspendModal = true"
        >
          Tạm ngưng
        </button>

        <button
          v-if="canRevoke"
          data-testid="cta-revoke"
          class="btn-ghost text-sm text-red-600 hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-500 rounded"
          @click="showRevokeModal = true"
        >
          Thu hồi
        </button>
      </template>
    </PageHeader>

    <div v-if="loading" class="card p-8 text-center text-slate-400">Đang tải…</div>

    <div v-else-if="error && !competency" class="card border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 flex items-center gap-3">
      <span class="flex-1">{{ error }}</span>
      <button class="text-sm underline focus-visible:ring-2 focus-visible:ring-rose-500 rounded" @click="load()">Thử lại</button>
    </div>

    <template v-else-if="competency">
      <!-- GATE-8: state CÓ hành động ở server nhưng user thiếu quyền → hint "không đủ quyền" -->
      <div
        v-if="showPermissionHint"
        data-testid="no-actions-hint"
        role="status"
        class="card p-4 bg-amber-50 border-amber-200 text-sm text-amber-800 flex items-start gap-3"
      >
        <svg class="w-5 h-5 shrink-0 text-amber-500 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
        </svg>
        <div>
          <p class="font-medium">Bạn không đủ quyền phê duyệt/tạm ngưng/khôi phục/thu hồi/tái chứng nhận năng lực.</p>
          <p class="text-xs mt-0.5">Liên hệ quản trị để cấp vai trò Quản lý đào tạo (Training Manager).</p>
        </div>
      </div>

      <!-- GATE-8: không có thao tác khả dụng (trạng thái kết thúc / chưa nạp allowed_transitions) -->
      <div
        v-else-if="showNoActionsHint"
        data-testid="no-actions-hint"
        role="status"
        class="card p-4 bg-slate-50 border-slate-200 text-sm text-slate-500 flex items-start gap-3"
      >
        <svg class="w-5 h-5 shrink-0 text-slate-400 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
        </svg>
        <div>
          <p class="font-medium">Không có thao tác khả dụng cho hồ sơ năng lực ở trạng thái hiện tại.</p>
        </div>
      </div>

      <!-- Main info -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b">Thông tin năng lực</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-5 text-sm">
          <div>
            <p class="text-xs text-slate-400 mb-1">Nhân viên</p>
            <p class="font-medium">{{ competency.user_full_name ?? competency.user }}</p>
            <p v-if="competency.user_full_name" class="text-xs text-slate-400 font-mono mt-0.5">{{ competency.user }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Device Model</p>
            <p class="font-medium" :title="competency.device_model">{{ competency.device_model_name ?? competency.device_model }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Chương trình đào tạo</p>
            <p>{{ competency.training_program }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Cấp độ năng lực</p>
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
              {{ levelLabel(competency.competency_level) }}
            </span>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày đạt được</p>
            <p>{{ competency.achieved_date }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày hết hạn</p>
            <p :class="competency.is_expired ? 'text-red-500 font-medium' : ''">{{ competency.expiry_date ?? '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Thời hạn còn lại</p>
            <p :class="expiryClass(competency.days_until_expiry)">{{ formatDays(competency.days_until_expiry) }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Hạn tái chứng nhận</p>
            <p>{{ competency.recertification_due_date ?? '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Khoa/Phòng</p>
            <p>{{ competency.department_at_assessment ?? '—' }}</p>
          </div>
        </div>
      </div>

      <!-- Assessment scores -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b">Kết quả đánh giá</h2>
        <!-- BUG-011: Hint khi chưa có điểm — giải thích scoring flow -->
        <div
          v-if="hasNoScores"
          class="mb-4 p-3 rounded-lg border border-blue-200 bg-blue-50 text-xs text-blue-700 flex items-start gap-2"
        >
          <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
          </svg>
          <div>
            <p class="font-medium">Chưa có điểm đánh giá.</p>
            <p class="mt-0.5">Điểm lý thuyết / thực hành được nhập trên <strong>Buổi đào tạo</strong> khi hoàn thành (trạng thái Đang diễn ra → Hoàn thành). Khi học viên đạt, hệ thống tự sinh hồ sơ năng lực với điểm tương ứng.</p>
          </div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-5 text-sm">
          <div>
            <p class="text-xs text-slate-400 mb-1">Điểm tổng cuối</p>
            <p class="text-2xl font-bold font-display tabular-nums" :class="competency.last_assessment_score != null && competency.last_assessment_score >= 60 ? 'text-emerald-600' : 'text-red-600'">
              {{ competency.last_assessment_score != null ? `${competency.last_assessment_score}%` : '—' }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Điểm lý thuyết</p>
            <p class="text-lg font-semibold text-slate-700">{{ competency.theory_score != null ? `${competency.theory_score}%` : '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Điểm thực hành</p>
            <p class="text-lg font-semibold text-slate-700">{{ competency.practical_score != null ? `${competency.practical_score}%` : '—' }}</p>
          </div>
        </div>
      </div>

      <!-- Signoff info -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b">Phê duyệt</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-5 text-sm">
          <div>
            <p class="text-xs text-slate-400 mb-1">Người phê duyệt</p>
            <p>{{ competency.supervisor_signoff ?? '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Ngày phê duyệt</p>
            <p>{{ competency.signoff_date ?? '—' }}</p>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="card p-8 text-center text-slate-400">Không tìm thấy bản ghi năng lực.</div>

    <!-- Revoke Modal -->
    <div v-if="showRevokeModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Thu hồi năng lực</h2>
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
          Sau khi thu hồi, nhân viên cần hoàn thành đào tạo lại để lấy lại năng lực.
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Lý do thu hồi <span class="text-red-500">*</span></label>
          <textarea
            v-model="revokeReason"
            rows="3"
            class="form-input w-full text-sm"
            placeholder="Nhập lý do thu hồi năng lực..."
          ></textarea>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Số hành động khắc phục/phòng ngừa liên quan (nếu có)</label>
          <input v-model="revokeCapa" type="text" class="form-input w-full text-sm" placeholder="CAPA-XXXX" />
        </div>
        <div class="flex justify-end gap-2">
          <button
            class="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50"
            @click="showRevokeModal = false; revokeReason = ''; revokeCapa = ''"
          >
            Quay lại
          </button>
          <button
            data-testid="confirm-revoke"
            :disabled="api.loading.value || !revokeReason.trim()"
            class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-red-500"
            @click="doRevoke"
          >
            {{ api.loading.value ? 'Đang xử lý...' : 'Xác nhận thu hồi' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Recertify Modal -->
    <div v-if="showRecertModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Tái chứng nhận năng lực</h2>
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
          Liên kết hồ sơ năng lực này với một buổi đào tạo nhắc lại (Refresher) để tái chứng nhận.
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Mã buổi đào tạo <span class="text-red-500">*</span></label>
          <input v-model="recertSession" type="text" class="form-input w-full text-sm" placeholder="TRN-2026-XXXXX" />
        </div>
        <div class="flex justify-end gap-2">
          <button
            class="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50"
            @click="showRecertModal = false; recertSession = ''"
          >
            Quay lại
          </button>
          <button
            data-testid="confirm-recertify"
            :disabled="api.loading.value || !recertSession.trim()"
            class="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500"
            @click="doRecertify"
          >
            {{ api.loading.value ? 'Đang xử lý...' : 'Xác nhận tái chứng nhận' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Suspend Modal (CR-WF-06-COMP) — reuse layout modal Thu hồi, lý do BẮT BUỘC -->
    <div v-if="showSuspendModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Tạm ngưng năng lực</h2>
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
          Sau khi tạm ngưng, nhân viên không được vận hành thiết bị cho tới khi năng lực được khôi phục.
        </div>
        <div>
          <label for="suspend-reason" class="block text-sm font-medium mb-1">Lý do tạm ngưng <span class="text-red-500">*</span></label>
          <textarea
            id="suspend-reason"
            v-model="suspendReason"
            rows="3"
            class="form-input w-full text-sm"
            placeholder="Nhập lý do tạm ngưng năng lực..."
          ></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button
            class="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-slate-400"
            @click="showSuspendModal = false; suspendReason = ''"
          >
            Quay lại
          </button>
          <button
            data-testid="confirm-suspend"
            :disabled="api.loading.value || !suspendReason.trim()"
            class="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-amber-500"
            @click="doSuspend"
          >
            {{ api.loading.value ? 'Đang xử lý...' : 'Xác nhận tạm ngưng' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Restore Modal (CR-WF-06-COMP) — xác nhận, không yêu cầu nhập liệu -->
    <div v-if="showRestoreModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div class="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
        <h2 class="font-semibold text-slate-800">Khôi phục năng lực</h2>
        <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs text-emerald-700">
          Khôi phục năng lực về trạng thái Hiệu lực để nhân viên được phép vận hành thiết bị trở lại.
        </div>
        <div class="flex justify-end gap-2">
          <button
            class="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-slate-400"
            @click="showRestoreModal = false"
          >
            Quay lại
          </button>
          <button
            data-testid="confirm-restore"
            :disabled="api.loading.value"
            class="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500"
            @click="doRestore"
          >
            {{ api.loading.value ? 'Đang xử lý...' : 'Xác nhận khôi phục' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
