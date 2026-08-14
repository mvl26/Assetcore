<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm09Store } from '@/stores/imm09'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/locales/messages'
import { attachRepairChecklistPhoto, type RepairChecklistRow } from '@/api/imm09'
import { ApiError } from '@/api/errors'

const props = defineProps<{ id: string }>()
const store = useImm09Store()
const router = useRouter()
const notify = useNotify()

const checklist = ref<RepairChecklistRow[]>([])
const deptHeadName = ref('')
const deptHeadTitle = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  if (!store.currentWO || store.currentWO.name !== props.id) {
    await store.fetchWorkOrder(props.id)
  }
  if (store.currentWO) {
    // CR-50: repair_checklist được BE seed sẵn danh mục chuẩn tại create_work_order
    // (mỗi phiếu CM mới có >=N dòng test_description + test_category, result TRỐNG cho
    // KTV nhập). KTV chỉ điền kết quả trên các dòng THẬT — KHÔNG fabricate dòng ở FE.
    // (Trước đây FE tự chèn 1 dòng "pass" generic khi rỗng để né deadlock BR-09-04 —
    //  đó là lỗ FE-side của chính BR-09-04, đã bỏ vì BE seed rows là SoT. Phiếu 0 dòng
    //  còn kẹt do khởi tạo trước fix → backfill_repair_checklists() ở BE xử lý, KHÔNG
    //  cho FE dựng pass giả — bảo toàn bất biến vacuous-pass: mọi 'Đạt' ⟺ dòng THẬT.)
    checklist.value = store.currentWO.repair_checklist.map(r => ({ ...r }))
  }
})

const passCount = computed(() => checklist.value.filter(r => r.result === 'Pass').length)
const totalCount = computed(() => checklist.value.length)
const progressPct = computed(() =>
  totalCount.value > 0 ? Math.round((passCount.value / totalCount.value) * 100) : 0
)
const hasAnyFail = computed(() => checklist.value.some(r => r.result === 'Fail'))
const allAnswered = computed(() => checklist.value.every(r => r.result !== null))

const canComplete = computed(() =>
  // totalCount>0: checklist rỗng ⇒ allAnswered vacuous-true → phải chặn ở đây, nếu không
  // nút bật rồi close_work_order/confirm_inspection 422 CHECKLIST_INCOMPLETE (BR-09-04).
  // BE seed rows nên phiếu CM mới luôn có dòng; guard này chỉ đỡ phiếu 0-dòng chưa backfill.
  totalCount.value > 0 &&
  allAnswered.value &&
  !hasAnyFail.value &&
  deptHeadName.value.trim() !== ''
)

function setResult(item: RepairChecklistRow, result: 'Pass' | 'Fail' | 'N/A') {
  item.result = result
}

// ─── AC-CR-84 · CỔNG ẢNH BẰNG CHỨNG NĐ98 ngay tại màn nghiệm thu (U1/U2) ───────
// Đây là nơi người dùng bấm «Hoàn thành sửa chữa» ⇒ lý do chặn phải hiện Ở ĐÂY, kèm
// đúng nút tải ảnh của từng mục (đường khắc phục tại chỗ). SERVER là SSoT:
// `evidence_photo_missing_idxs` = ĐÚNG tập mà `close_work_order` từ chối (INV-CMEVID-1)
// ⇒ FE KHÔNG đếm lại từ `item.photo` (bản diễn giải thứ hai) và KHÔNG tự khoá nút
// (validator server mới là cổng — nút giữ nguyên điều kiện nghiệp vụ cũ).
// Sau mỗi lần đính ảnh, `onPhotoSelected` đã refetch phiếu ⇒ tập này tự cập nhật.
const evidenceGateApplies = computed(() => store.currentWO?.evidence_photo_required === 1)
const evidenceMissingIdxs = computed<number[]>(() => {
  const raw = store.currentWO?.evidence_photo_missing_idxs
  return Array.isArray(raw)
    ? raw.filter((n): n is number => typeof n === 'number' && Number.isFinite(n))
    : []
})
const evidenceTotalRequired = computed(() => {
  const n = store.currentWO?.evidence_photo_total_required
  return typeof n === 'number' && Number.isFinite(n) && n > 0 ? Math.trunc(n) : 0
})
const evidenceDoneCount = computed(() =>
  Math.max(0, evidenceTotalRequired.value - evidenceMissingIdxs.value.length),
)
const evidenceComplete = computed(
  () => evidenceGateApplies.value && evidenceMissingIdxs.value.length === 0,
)
function isEvidenceMissing(idx: number): boolean {
  return evidenceGateApplies.value && evidenceMissingIdxs.value.includes(Number(idx))
}
/** Thông điệp lỗi server neo DƯỚI bảng checklist (envelope `fields.repair_checklist`). */
const checklistFieldError = ref<string | null>(null)

// ── Ảnh bằng chứng mỗi mục checklist (NĐ98 Class C/D — mobile CR-15/G6) ────────
// Đối xứng IncidentDetailView. Tối đa 1 ảnh/mục (Attach ĐƠN, BE là SoT).
const uploadingIdx = ref<number | null>(null)              // idx mục đang upload
const photoErrors = reactive<Record<number, string>>({})   // lỗi VN inline theo idx
// KHÔNG reactive: chỉ giữ tham chiếu <input> ẩn để .click() trong handler (tránh Vue
// bọc proxy lên DOM node → cảnh báo).
const fileInputs: Record<number, HTMLInputElement | null> = {}

function setFileInput(idx: number, el: unknown) {
  fileInputs[idx] = (el as HTMLInputElement | null) ?? null
}

function triggerPhotoPicker(idx: number) {
  photoErrors[idx] = ''
  fileInputs[idx]?.click()
}

async function onPhotoSelected(item: RepairChecklistRow, e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  photoErrors[item.idx] = ''
  uploadingIdx.value = item.idx
  try {
    // LL-FE-47: truyền ĐÚNG File user chọn + idx của mục (KHÔNG hardcode call-site).
    const res = await attachRepairChecklistPhoto(props.id, item.idx, file)
    item.photo = res.file_url                    // authoritative → nút chuyển "đã đính"
    await store.fetchWorkOrder(props.id)         // refetch WO (đồng bộ store + màn chi tiết)
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: `ảnh bằng chứng mục #${item.idx}` } })
  } catch (e2: unknown) {
    // VALIDATION (sai định dạng / quá dung lượng / đã đủ ảnh) → thông điệp VN inline
    // dưới control. System/khác → notify.fromError (toast/modal), inline giữ generic.
    if (e2 instanceof ApiError && e2.fields?.file) {
      photoErrors[item.idx] = e2.fields.file
    } else if (e2 instanceof ApiError) {
      photoErrors[item.idx] = e2.message
      notify.fromError(e2)
    } else {
      photoErrors[item.idx] = e2 instanceof Error ? e2.message : 'Không thể đính ảnh bằng chứng'
    }
  } finally {
    uploadingIdx.value = null
    if (input) input.value = ''                  // reset để chọn lại cùng file được
  }
}

function resultButtonClass(item: RepairChecklistRow, result: 'Pass' | 'Fail' | 'N/A'): string {
  const active = item.result === result
  const base = 'px-3 py-1 rounded text-xs font-semibold border transition-all duration-150'
  if (result === 'Pass') {
    return active
      ? `${base} bg-green-600 border-green-600 text-white`
      : `${base} border-slate-300 text-slate-600 hover:border-green-400 hover:text-green-600`
  }
  if (result === 'Fail') {
    return active
      ? `${base} bg-red-600 border-red-600 text-white`
      : `${base} border-slate-300 text-slate-600 hover:border-red-400 hover:text-red-600`
  }
  return active
    ? `${base} bg-slate-500 border-gray-500 text-white`
    : `${base} border-slate-300 text-slate-600 hover:border-slate-400`
}

async function handleComplete() {
  if (!canComplete.value) return
  submitting.value = true
  error.value = null
  checklistFieldError.value = null
  // CR-24 idempotency: sinh khoá 1 lần cho mỗi lần bấm "Hoàn thành sửa chữa".
  // Ổn định qua auto-retry (axios/interceptor replay CÙNG request → CÙNG khoá →
  // BE replay success-envelope, không tạo transition/Lifecycle Event trùng); đổi
  // khi user chủ động bấm lại (handler chạy lại → khoá mới).
  const clientRequestId = globalThis.crypto.randomUUID()
  try {
    const ok = await store.doCloseWorkOrder({
      name: props.id,
      repair_summary: '',
      root_cause_category: store.currentWO?.root_cause_category ?? '',
      dept_head_name: `${deptHeadName.value} — ${deptHeadTitle.value}`,
      checklist_results: checklist.value,
      client_request_id: clientRequestId,
    })
    if (ok) {
      notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: 'hoàn thành sửa chữa' } })
      router.push(`/cm/work-orders/${props.id}`)
    } else {
      notify.fromError(store.lastApiError)
      error.value = store.error ?? 'Không thể hoàn thành sửa chữa'
      // AC-CR-84 §3: envelope từ chối vì thiếu ảnh bằng chứng neo `fields.repair_checklist`
      // ⇒ (b) hiện thông điệp SERVER ngay dưới bảng nghiệm thu (đúng chỗ khắc phục) và
      // (c) refetch phiếu để tập mục-thiếu-ảnh cập nhật (người dùng có thể vừa đính ảnh ở
      // tab khác). KHÔNG coi là lỗi hệ thống, KHÔNG đăng xuất.
      const fieldMsg = store.lastApiError?.fields?.repair_checklist
      if (fieldMsg) {
        checklistFieldError.value = fieldMsg
        await store.fetchWorkOrder(props.id)
      }
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <button
        class="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
        @click="router.push(`/cm/work-orders/${id}`)"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest">Nghiệm thu</p>
        <h1 class="text-xl font-bold text-slate-900">Nghiệm thu sau sửa chữa — {{ id }}</h1>
      </div>
    </div>

    <!-- Error banner -->
    <Transition name="fade">
      <div v-if="error" class="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
        {{ error }}
      </div>
    </Transition>

    <div class="space-y-5">
      <!-- Progress bar -->
      <div class="card">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-semibold text-slate-700">Tiến độ nghiệm thu</span>
          <span class="text-sm font-medium text-slate-600">{{ passCount }} / {{ totalCount }} mục Đạt</span>
        </div>
        <div class="h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            :class="[
              'h-3 rounded-full transition-all duration-500',
              hasAnyFail ? 'bg-red-600' : progressPct === 100 ? 'bg-emerald-500' : 'bg-brand-600'
            ]"
            :style="{ width: `${progressPct}%` }"
          />
        </div>
        <div class="flex justify-between mt-2 text-xs text-slate-400">
          <span>{{ progressPct }}% hoàn thành</span>
          <span v-if="hasAnyFail" class="text-red-600 font-medium">Có mục Không đạt — không thể hoàn thành</span>
          <span v-else-if="allAnswered && progressPct === 100" class="text-emerald-600 font-medium">Tất cả đã Đạt</span>
        </div>
      </div>

      <!-- AC-CR-84 (U1) — dải trạng thái ảnh bằng chứng NĐ98, CHỈ khi server báo cổng áp
           dụng (`evidence_photo_required === 1` = thiết bị nhóm nguy cơ cao). Số liệu
           NGUYÊN VĂN từ server; FE không đếm lại từ `item.photo`. Vắng khoá (worker BE
           chưa reload) ⇒ ẩn hoàn toàn, KHÔNG khẳng định "đã đủ ảnh". -->
      <div
        v-if="evidenceGateApplies"
        data-testid="cm-checklist-evidence-banner"
        role="status"
        :class="[
          'card border',
          evidenceComplete ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50',
        ]"
      >
        <p :class="['text-sm font-medium', evidenceComplete ? 'text-emerald-800' : 'text-amber-900']">
          <template v-if="evidenceComplete">
            Bằng chứng NĐ98: đã có ảnh {{ evidenceDoneCount }}/{{ evidenceTotalRequired }} mục
          </template>
          <template v-else>
            Bằng chứng NĐ98: còn {{ evidenceMissingIdxs.length }}/{{ evidenceTotalRequired }} mục chưa có ảnh — cần đính đủ trước khi hoàn thành sửa chữa
          </template>
        </p>
        <p v-if="!evidenceComplete" class="mt-1 text-xs text-amber-800">
          Đã có {{ evidenceDoneCount }}/{{ evidenceTotalRequired }} mục có ảnh. Dùng nút “Đính ảnh” ở từng mục bên dưới để bổ sung.
        </p>
      </div>

      <!-- Checklist items -->
      <div v-if="checklist.length === 0" class="card text-center py-8">
        <p class="text-sm font-medium text-slate-600">Phiếu sửa chữa này chưa có mục nghiệm thu nào.</p>
        <p class="mt-1 text-xs text-slate-400">
          Danh mục nghiệm thu chuẩn được tạo tự động khi mở phiếu. Nếu phiếu cũ chưa có,
          liên hệ quản trị để bổ sung danh mục trước khi nghiệm thu.
        </p>
        <button
          type="button"
          class="mt-4 px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="router.push(`/cm/work-orders/${id}`)"
        >
          Quay lại phiếu sửa chữa
        </button>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="item in checklist"
          :key="item.idx"
          :class="[
            'card transition-all duration-200',
            item.result === 'Pass' ? 'border-emerald-200 bg-emerald-50/60' :
            item.result === 'Fail' ? 'border-red-200 bg-red-50/60' :
            item.result === 'N/A' ? 'border-slate-200 bg-slate-50/60' : 'border-slate-200'
          ]"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-xs font-semibold text-slate-400">#{{ item.idx }}</span>
                <span class="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{{ item.test_category }}</span>
              </div>
              <p class="text-sm font-medium text-slate-800">{{ item.test_description }}</p>
              <div v-if="item.expected_value || item.measured_value" class="flex gap-4 mt-1.5 text-xs text-slate-500">
                <span v-if="item.expected_value">Yêu cầu: <strong>{{ item.expected_value }}</strong></span>
                <span v-if="item.measured_value">Đo được: <strong>{{ item.measured_value }}</strong></span>
              </div>
              <p v-if="item.result === 'Fail'" class="mt-1.5 text-xs font-semibold text-red-600">
                Kết quả Không đạt — không thể hoàn thành nghiệm thu
              </p>
            </div>
            <!-- Result buttons -->
            <div class="flex gap-1.5 shrink-0">
              <button :class="resultButtonClass(item, 'Pass')" @click="setResult(item, 'Pass')">Đạt</button>
              <button :class="resultButtonClass(item, 'Fail')" @click="setResult(item, 'Fail')">Không đạt</button>
              <button :class="resultButtonClass(item, 'N/A')" @click="setResult(item, 'N/A')">Không áp dụng</button>
            </div>
          </div>
          <!-- Notes field -->
          <div v-if="item.result === 'Fail' || item.result === 'N/A'" class="mt-3">
            <input
              v-model="item.notes"
              type="text"
              :class="[
                'w-full border rounded px-3 py-1.5 text-xs',
                item.result === 'Fail' ? 'border-red-300 bg-white' : 'border-slate-300'
              ]"
              placeholder="Ghi chú (tùy chọn)..."
            />
          </div>

          <!-- Ảnh bằng chứng mục (NĐ98 Class C/D — tối đa 1 ảnh/mục) -->
          <div class="mt-3 flex items-center gap-3 flex-wrap">
            <a
              v-if="item.photo"
              :href="item.photo"
              target="_blank"
              rel="noopener"
              class="rounded-lg overflow-hidden border border-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              :aria-label="`Xem ảnh bằng chứng mục #${item.idx}`"
            >
              <img
                :src="item.photo"
                :alt="`Ảnh bằng chứng mục #${item.idx} — ${item.test_description}`"
                class="h-16 w-16 object-cover"
                loading="lazy"
              >
            </a>
            <!-- input file ẩn (a11y: kích hoạt qua nút chữ có nhãn rõ ràng) -->
            <input
              :ref="el => setFileInput(item.idx, el)"
              type="file"
              accept="image/jpeg,image/png"
              class="sr-only"
              tabindex="-1"
              aria-hidden="true"
              @change="onPhotoSelected(item, $event)"
            >
            <button
              type="button"
              :disabled="!!item.photo || uploadingIdx === item.idx"
              class="px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              :aria-label="`Đính ảnh bằng chứng mục #${item.idx} (JPG hoặc PNG)`"
              @click="triggerPhotoPicker(item.idx)"
            >
              <span v-if="item.photo">Đã đính ảnh bằng chứng</span>
              <span v-else-if="uploadingIdx === item.idx">Đang tải lên...</span>
              <span v-else>+ Đính ảnh (JPG hoặc PNG)</span>
            </button>
            <!-- AC-CR-84 (U2) — mục nằm trong tập SERVER báo thiếu ảnh: nhãn CHỮ, không
                 chỉ phân biệt bằng màu; nguồn `evidence_photo_missing_idxs`. -->
            <span
              v-if="isEvidenceMissing(item.idx)"
              data-testid="cm-checklist-evidence-chip"
              class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
            >
              Chưa có ảnh bằng chứng (bắt buộc)
            </span>
          </div>
          <!-- Lỗi VALIDATION inline VN dưới control -->
          <p v-if="photoErrors[item.idx]" class="mt-1.5 text-xs text-red-600" role="alert">
            {{ photoErrors[item.idx] }}
          </p>
        </div>
      </div>

      <!-- AC-CR-84 §3(b) — lỗi server neo Ở ĐÚNG bảng nghiệm thu (envelope
           `fields.repair_checklist`), thông điệp NGUYÊN VĂN tiếng Việt của server. -->
      <p
        v-if="checklistFieldError"
        data-testid="cm-checklist-field-error"
        role="alert"
        class="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
      >
        {{ checklistFieldError }}
      </p>

      <!-- Dept head confirmation -->
      <div class="card">
        <p class="text-sm font-semibold text-slate-700 mb-3">
          Xác nhận trưởng khoa phòng <span class="text-red-500">*</span>
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-slate-500 mb-1">Họ tên *</label>
            <input
              v-model="deptHeadName"
              type="text"
              class="form-input"
              placeholder="Nguyễn Văn A"
            />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">Chức danh</label>
            <input
              v-model="deptHeadTitle"
              type="text"
              class="form-input"
              placeholder="Trưởng khoa ICU"
            />
          </div>
        </div>
        <p v-if="!deptHeadName.trim() && allAnswered && !hasAnyFail" class="mt-2 text-xs text-red-500">
          Bắt buộc nhập họ tên trưởng khoa
        </p>
      </div>

      <!-- Actions -->
      <div class="flex justify-between items-center pt-2 pb-6">
        <button
          class="px-5 py-2.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          @click="router.push(`/cm/work-orders/${id}`)"
        >
          Quay lại
        </button>
        <button
          :disabled="!canComplete || submitting"
          :class="[
            'px-6 py-2.5 rounded-lg text-sm font-semibold text-white transition-all duration-150',
            canComplete && !submitting
              ? 'bg-green-600 hover:bg-green-700 shadow-sm'
              : 'bg-green-300 cursor-not-allowed'
          ]"
          @click="handleComplete"
        >
          {{ submitting ? 'Đang xử lý...' : 'Hoàn thành sửa chữa' }}
        </button>
      </div>

      <!-- Hint when not ready -->
      <Transition name="fade">
        <div v-if="!canComplete && checklist.length > 0" class="pb-4 text-xs text-slate-400 text-center">
          <span v-if="!allAnswered">Cần điền đầy đủ kết quả cho tất cả {{ totalCount - passCount - checklist.filter(r => r.result === 'Fail' || r.result === 'N/A').length }} mục chưa chọn</span>
          <span v-else-if="hasAnyFail">Có {{ checklist.filter(r => r.result === 'Fail').length }} mục Không đạt — cần xử lý trước khi hoàn thành</span>
          <span v-else-if="!deptHeadName.trim()">Cần nhập họ tên trưởng khoa phòng</span>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-up-enter-active { transition: all 0.3s ease-out; }
.slide-up-enter-from { transform: translateY(8px); opacity: 0; }
</style>
