<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useImm06Store } from '@/stores/imm06'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import type { MasterItem } from '@/stores/useMasterDataStore'
import { formatDate } from '@/utils/docUtils'
import type { TrainingSessionSummary } from '@/api/imm06'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store  = useImm06Store()

const doc       = computed(() => store.currentHr)
const activeTab = ref<'info' | 'training' | 'lifecycle'>('info')

// ─── Training Schedule Modal ───────────────────────────────────────────────────
const showScheduleModal = ref(false)
const scheduleForm = ref({
  training_type:  'Operation',
  trainer:        '',
  training_date:  '',
  duration_hours: 2,
  trainees:       [] as Array<{ trainee_user: string; role: string }>,
})

function addTraineeRow() {
  scheduleForm.value.trainees.push({ trainee_user: '', role: '' })
}
function removeTraineeRow(i: number) {
  scheduleForm.value.trainees.splice(i, 1)
}

async function handleSchedule() {
  if (!scheduleForm.value.trainer || !scheduleForm.value.training_date) return
  const name = await store.doScheduleTraining({
    handover_name: props.id,
    training_type: scheduleForm.value.training_type,
    trainer:       scheduleForm.value.trainer,
    training_date: scheduleForm.value.training_date,
    duration_hours:scheduleForm.value.duration_hours,
    trainees:      scheduleForm.value.trainees.filter(t => t.trainee_user),
  })
  if (name) {
    showScheduleModal.value = false
    resetScheduleForm()
    activeTab.value = 'training'
  }
}

function resetScheduleForm() {
  scheduleForm.value = { training_type: 'Operation', trainer: '', training_date: '', duration_hours: 2, trainees: [] }
}

// ─── Complete Training Modal ───────────────────────────────────────────────────
const showCompleteModal    = ref(false)
const selectedSession      = ref<TrainingSessionSummary | null>(null)
const completeScores       = ref<Array<{ trainee_user: string; full_name: string; score: number; passed: boolean }>>([])
const completeNotes        = ref('')

async function openCompleteModal(session: TrainingSessionSummary) {
  selectedSession.value = session
  // Load trainees for the session
  try {
    const { frappeGet } = await import('@/api/helpers')
    const rows = await frappeGet<Array<{ trainee_user: string; full_name: string }> >(
      '/api/method/frappe.client.get_list',
      { doctype: 'Training Trainee', parent: session.name, fields: JSON.stringify(['trainee_user', 'full_name']) },
    )
    completeScores.value = rows.map(r => ({ trainee_user: r.trainee_user, full_name: r.full_name, score: 0, passed: false }))
  } catch {
    completeScores.value = []
  }
  showCompleteModal.value = true
}

async function handleCompleteTraining() {
  if (!selectedSession.value) return
  const ok = await store.doCompleteTraining({
    training_session_name: selectedSession.value.name,
    scores: completeScores.value.map(s => ({ trainee_user: s.trainee_user, score: s.score, passed: s.passed })),
    notes: completeNotes.value,
  })
  if (ok) {
    showCompleteModal.value = false
    selectedSession.value = null
    completeNotes.value = ''
  }
}

// ─── Confirm Handover Modal ────────────────────────────────────────────────────
const showConfirmModal  = ref(false)
const confirmSignoff    = ref('')
const confirmNotes      = ref('')

async function handleConfirmHandover() {
  if (!confirmSignoff.value) return
  const ok = await store.doConfirmHandover({
    name:              props.id,
    dept_head_signoff: confirmSignoff.value,
    notes:             confirmNotes.value,
  })
  if (ok) {
    showConfirmModal.value = false
    confirmSignoff.value = ''
    confirmNotes.value = ''
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatBudget(v: number | null | undefined) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN').format(v)
}

function sessionStatusColor(s: string) {
  const map: Record<string, string> = {
    Scheduled: 'bg-blue-50 text-blue-700',
    Completed: 'bg-emerald-50 text-emerald-700',
    Cancelled: 'bg-red-50 text-red-600',
  }
  return map[s] ?? 'bg-slate-100 text-slate-500'
}

// ─── Load ─────────────────────────────────────────────────────────────────────
async function load() { await store.fetchHr(props.id) }
onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/handover')">
        Bàn giao & Đào tạo
      </button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-mono font-semibold text-slate-700">{{ id }}</span>
      <StatusBadge v-if="doc" :state="doc.status" size="xs" class="ml-1" />
    </nav>

    <SkeletonLoader v-if="store.loading && !doc" variant="form" />

    <div v-else-if="store.error && !doc" class="alert-error">
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline" @click="load">Thử lại</button>
    </div>

    <template v-else-if="doc">

      <!-- Page header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-06 · Phiếu Bàn giao</p>
          <h1 class="text-2xl font-bold text-slate-900 font-mono">{{ doc.name }}</h1>
          <div class="flex items-center gap-2 mt-2">
            <StatusBadge :state="doc.status" size="md" />
            <span class="text-xs text-slate-400">{{ doc.handover_type }}</span>
          </div>
        </div>

        <!-- Action buttons based on workflow state -->
        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
          <button
            v-if="store.canScheduleTraining && !store.isFinished"
            class="btn-primary"
            :disabled="store.loading"
            @click="showScheduleModal = true; store.error = null"
          >
            Lên lịch đào tạo
          </button>
          <button
            v-if="store.canCompleteTraining"
            class="btn-primary"
            :disabled="store.loading"
            @click="activeTab = 'training'"
          >
            Xem đào tạo
          </button>
          <button
            v-if="store.canConfirmHandover"
            class="btn-primary"
            :disabled="store.loading"
            @click="showConfirmModal = true; store.error = null"
          >
            Ký nhận bàn giao
          </button>
          <button class="btn-ghost" @click="router.back()">Quay lại</button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="store.error" class="alert-error mb-5">
        <span class="flex-1">{{ store.error }}</span>
        <button class="text-xs font-medium" @click="store.error = null">✕</button>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 mb-6 bg-slate-100 p-1 rounded-xl w-fit">
        <button
          v-for="tab in [
            { key: 'info',      label: 'Thông tin bàn giao' },
            { key: 'training',  label: `Đào tạo (${doc.training_sessions?.length ?? 0})` },
            { key: 'lifecycle', label: 'Lịch sử vòng đời' },
          ]"
          :key="tab.key"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeTab === tab.key
            ? 'bg-white text-slate-900 shadow-sm'
            : 'text-slate-500 hover:text-slate-700'"
          @click="activeTab = tab.key as typeof activeTab"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Tab: Thông tin bàn giao -->
      <template v-if="activeTab === 'info'">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div class="card animate-slide-up" style="animation-delay:0ms">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
              Thông tin cơ bản
            </h3>
            <dl class="space-y-3">
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Thiết bị</dt>
                <dd class="text-sm font-mono font-semibold text-slate-800">{{ doc.asset }}</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Khoa nhận</dt>
                <dd class="text-sm font-medium text-slate-800">{{ doc.clinical_dept }}</dd>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Ngày bàn giao</dt>
                  <dd class="text-sm text-slate-700">{{ formatDate(doc.handover_date) }}</dd>
                </div>
                <div>
                  <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Loại</dt>
                  <dd class="text-sm text-slate-700">{{ doc.handover_type }}</dd>
                </div>
              </div>
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Người nhận đại diện</dt>
                <dd class="text-sm text-slate-700">{{ doc.received_by }}</dd>
              </div>
              <div v-if="doc.conditions_if_conditional">
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Điều kiện bàn giao</dt>
                <dd class="text-sm text-amber-800 bg-amber-50 px-3 py-2 rounded-lg border border-amber-100">
                  {{ doc.conditions_if_conditional }}
                </dd>
              </div>
            </dl>
          </div>

          <div class="card animate-slide-up" style="animation-delay:40ms">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
              Liên kết & Chữ ký
            </h3>
            <dl class="space-y-3">
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Phiếu Commissioning</dt>
                <dd>
                  <button
                    class="text-sm font-mono text-brand-600 hover:underline"
                    @click="router.push(`/commissioning/${doc.commissioning_ref}`)"
                  >
                    {{ doc.commissioning_ref }} →
                  </button>
                </dd>
              </div>
              <div v-if="doc.htm_engineer_signoff">
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Kỹ sư HTM ký</dt>
                <dd class="text-sm text-slate-700">{{ doc.htm_engineer_signoff }}</dd>
              </div>
              <div v-if="doc.dept_head_signoff">
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Trưởng khoa ký</dt>
                <dd class="text-sm font-semibold text-emerald-700">{{ doc.dept_head_signoff }}</dd>
              </div>
            </dl>

            <div v-if="doc.handover_notes" class="mt-4 pt-4 border-t border-slate-100">
              <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Ghi chú bàn giao</p>
              <p class="text-sm text-slate-700 whitespace-pre-line">{{ doc.handover_notes }}</p>
            </div>
          </div>
        </div>
      </template>

      <!-- Tab: Đào tạo -->
      <template v-if="activeTab === 'training'">
        <div class="mb-4 flex items-center justify-between">
          <p class="text-sm text-slate-500">
            {{ doc.training_sessions?.length ?? 0 }} buổi đào tạo được lập
          </p>
          <button
            v-if="store.canScheduleTraining && !store.isFinished"
            class="btn-primary text-xs"
            @click="showScheduleModal = true; store.error = null"
          >
            + Lên lịch đào tạo
          </button>
        </div>

        <div v-if="!doc.training_sessions?.length"
             class="card py-12 text-center text-slate-400 animate-slide-up">
          <svg class="w-10 h-10 mx-auto opacity-25 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <p class="text-sm">Chưa có buổi đào tạo nào. Lên lịch buổi đầu tiên.</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="(s, i) in doc.training_sessions"
            :key="s.name"
            class="card animate-slide-up"
            :style="`animation-delay:${i * 30}ms`"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span class="font-mono text-xs text-brand-600 font-semibold">{{ s.name }}</span>
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold" :class="sessionStatusColor(s.status)">
                    {{ s.status === 'Scheduled' ? 'Đã lên lịch' : s.status === 'Completed' ? 'Hoàn thành' : 'Đã hủy' }}
                  </span>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-slate-600">
                  <div>
                    <p class="text-slate-400 mb-0.5">Loại đào tạo</p>
                    <p class="font-medium">{{ s.training_type }}</p>
                  </div>
                  <div>
                    <p class="text-slate-400 mb-0.5">Ngày</p>
                    <p class="font-medium">{{ formatDate(s.training_date) }}</p>
                  </div>
                  <div>
                    <p class="text-slate-400 mb-0.5">Trainer</p>
                    <p class="font-medium">{{ s.trainer }}</p>
                  </div>
                  <div v-if="s.status === 'Completed'">
                    <p class="text-slate-400 mb-0.5">Kết quả</p>
                    <p class="font-semibold" :class="(s.passed_count ?? 0) === (s.trainees_count ?? 0) ? 'text-emerald-600' : 'text-amber-600'">
                      {{ s.passed_count }}/{{ s.trainees_count }} đạt
                    </p>
                  </div>
                </div>
                <!-- Progress bar for completed sessions -->
                <div v-if="s.status === 'Completed' && (s.trainees_count ?? 0) > 0" class="mt-2">
                  <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all"
                      :class="(s.passed_count ?? 0) === (s.trainees_count ?? 0) ? 'bg-emerald-500' : 'bg-amber-500'"
                      :style="`width:${Math.round(((s.passed_count ?? 0) / (s.trainees_count ?? 1)) * 100)}%`"
                    />
                  </div>
                </div>
              </div>
              <button
                v-if="s.status === 'Scheduled' && store.canCompleteTraining"
                class="btn-ghost text-xs shrink-0 ml-4"
                @click="openCompleteModal(s)"
              >
                Ghi nhận kết quả
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- Tab: Lịch sử vòng đời -->
      <template v-if="activeTab === 'lifecycle'">
        <div v-if="!doc.lifecycle_events?.length" class="card py-12 text-center text-slate-400">
          <p class="text-sm">Chưa có sự kiện vòng đời nào.</p>
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="(ev, i) in doc.lifecycle_events"
            :key="ev.name"
            class="flex gap-4 animate-fade-in"
            :style="`animation-delay:${i * 20}ms`"
          >
            <div class="flex flex-col items-center">
              <div class="w-2.5 h-2.5 rounded-full bg-brand-500 mt-1.5 shrink-0" />
              <div v-if="i < (doc.lifecycle_events?.length ?? 0) - 1" class="flex-1 w-px bg-slate-200 my-1" />
            </div>
            <div class="card flex-1 mb-3">
              <div class="flex items-start justify-between">
                <div>
                  <p class="text-xs font-semibold text-brand-700 mb-0.5">{{ ev.event_type }}</p>
                  <p class="text-xs text-slate-500">
                    {{ ev.from_status }} → {{ ev.to_status }}
                  </p>
                  <p v-if="ev.notes" class="text-xs text-slate-600 mt-1">{{ ev.notes }}</p>
                </div>
                <div class="text-right shrink-0 ml-4">
                  <p class="text-xs text-slate-400">{{ ev.actor }}</p>
                  <p class="text-xs text-slate-400">{{ formatDate(ev.timestamp) }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

    </template>

    <!-- ── Modal: Lên lịch đào tạo ─────────────────────────────────────────── -->
    <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0"
                enter-to-class="opacity-100" leave-active-class="transition duration-100 ease-in"
                leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="showScheduleModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showScheduleModal = false; resetScheduleForm()">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
          <h3 class="text-base font-semibold text-slate-800 mb-1">Lên lịch Đào tạo</h3>
          <p class="text-sm text-slate-500 mb-5">Tạo buổi đào tạo vận hành cho phiếu bàn giao {{ id }}</p>

          <div v-if="store.error" class="alert-error mb-4 text-sm">{{ store.error }}</div>

          <div class="space-y-4">
            <div class="form-group">
              <label class="form-label">Loại đào tạo <span class="text-red-500">*</span></label>
              <select v-model="scheduleForm.training_type" class="form-select">
                <option v-for="t in ['Operation','Safety','Emergency','Maintenance','Full']" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="form-group">
                <label class="form-label">Trainer <span class="text-red-500">*</span></label>
                <SmartSelect
                  doctype="User"
                  placeholder="Tìm trainer..."
                  :model-value="scheduleForm.trainer"
                  @select="(item: MasterItem) => scheduleForm.trainer = item.id"
                  @clear="() => scheduleForm.trainer = ''"
                />
              </div>
              <div class="form-group">
                <label class="form-label">Ngày đào tạo <span class="text-red-500">*</span></label>
                <input v-model="scheduleForm.training_date" type="date" class="form-input" />
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Thời lượng (giờ)</label>
              <input v-model.number="scheduleForm.duration_hours" type="number" min="0.5" step="0.5" class="form-input" />
            </div>

            <!-- Trainees -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="form-label mb-0">Danh sách học viên</label>
                <button type="button" class="text-xs text-brand-600 hover:underline" @click="addTraineeRow">+ Thêm học viên</button>
              </div>
              <div v-for="(t, i) in scheduleForm.trainees" :key="i" class="flex gap-2 mb-2">
                <div class="flex-1">
                  <SmartSelect
                    doctype="User"
                    placeholder="Tìm học viên..."
                    :model-value="t.trainee_user"
                    @select="(item: MasterItem) => scheduleForm.trainees[i].trainee_user = item.id"
                    @clear="() => scheduleForm.trainees[i].trainee_user = ''"
                  />
                </div>
                <input v-model="t.role" type="text" class="form-input w-32 text-xs" placeholder="Vai trò" />
                <button type="button" class="text-slate-300 hover:text-red-500 transition-colors" @click="removeTraineeRow(i)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p v-if="scheduleForm.trainees.length === 0" class="text-xs text-slate-400 italic">
                Có thể thêm học viên sau khi tạo phiếu
              </p>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showScheduleModal = false; resetScheduleForm()">Hủy</button>
            <button
              class="btn-primary"
              :disabled="store.loading || !scheduleForm.trainer || !scheduleForm.training_date"
              @click="handleSchedule"
            >
              <svg v-if="store.loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Lưu lịch đào tạo
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal: Ghi nhận kết quả đào tạo ────────────────────────────────── -->
    <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0"
                enter-to-class="opacity-100" leave-active-class="transition duration-100 ease-in"
                leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="showCompleteModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showCompleteModal = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
          <h3 class="text-base font-semibold text-slate-800 mb-1">Ghi nhận kết quả đào tạo</h3>
          <p class="text-sm text-slate-500 mb-5">{{ selectedSession?.name }} — {{ selectedSession?.training_type }}</p>

          <div v-if="store.error" class="alert-error mb-4 text-sm">{{ store.error }}</div>

          <!-- Score table -->
          <div v-if="completeScores.length > 0" class="mb-4">
            <div class="grid grid-cols-12 gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wide mb-2 px-1">
              <span class="col-span-5">Học viên</span>
              <span class="col-span-3 text-center">Điểm (0-100)</span>
              <span class="col-span-4 text-center">Đạt (≥70)</span>
            </div>
            <div v-for="s in completeScores" :key="s.trainee_user" class="grid grid-cols-12 gap-2 items-center mb-2">
              <span class="col-span-5 text-sm text-slate-700">{{ s.full_name || s.trainee_user }}</span>
              <input
                v-model.number="s.score"
                type="number" min="0" max="100"
                class="col-span-3 form-input text-center text-sm"
                @input="s.passed = s.score >= 70"
              />
              <div class="col-span-4 flex justify-center">
                <input type="checkbox" v-model="s.passed" class="w-4 h-4 accent-emerald-600" />
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-slate-400 italic mb-4">Không có học viên đã đăng ký. Buổi học vẫn có thể được đánh dấu hoàn thành.</p>

          <div class="form-group">
            <label class="form-label">Ghi chú buổi học</label>
            <textarea v-model="completeNotes" rows="3" class="form-input resize-none"
                      placeholder="Nhận xét, nội dung đã học, vấn đề phát sinh..." />
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showCompleteModal = false">Hủy</button>
            <button class="btn-primary" :disabled="store.loading" @click="handleCompleteTraining">
              <svg v-if="store.loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Lưu kết quả
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Modal: Ký nhận bàn giao ────────────────────────────────────────── -->
    <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0"
                enter-to-class="opacity-100" leave-active-class="transition duration-100 ease-in"
                leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="showConfirmModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showConfirmModal = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
          <h3 class="text-base font-semibold text-slate-800 mb-1">Ký nhận Bàn giao</h3>
          <p class="text-sm text-slate-500 mb-5">
            Xác nhận Trưởng khoa đã kiểm tra và chấp nhận bàn giao thiết bị <strong>{{ doc?.asset }}</strong>.
          </p>

          <div v-if="store.error" class="alert-error mb-4 text-sm">{{ store.error }}</div>

          <div class="form-group mb-4">
            <label class="form-label">Trưởng khoa ký nhận <span class="text-red-500">*</span></label>
            <SmartSelect
              doctype="User"
              placeholder="Chọn Trưởng khoa..."
              :model-value="confirmSignoff"
              @select="(item: MasterItem) => confirmSignoff = item.id"
              @clear="() => confirmSignoff = ''"
            />
          </div>
          <div class="form-group">
            <label class="form-label">Ghi chú xác nhận <span class="text-slate-400 text-xs">(tùy chọn)</span></label>
            <textarea v-model="confirmNotes" rows="3" class="form-input resize-none"
                      placeholder="Ghi chú về tình trạng thiết bị lúc bàn giao, phụ kiện kèm theo..." />
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showConfirmModal = false">Hủy</button>
            <button
              class="btn-primary"
              :disabled="store.loading || !confirmSignoff"
              @click="handleConfirmHandover"
            >
              <svg v-if="store.loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Xác nhận bàn giao
            </button>
          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>
