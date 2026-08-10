<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useImm05Store } from '@/stores/imm05'
import { submitForReview as apiSubmitForReview, archiveDocument as apiArchiveDocument } from '@/api/imm05'
import type { AssetDocumentDetail } from '@/api/imm05'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
import { toApiError } from '@/api/errors'
import { formatDate } from '@/utils/docUtils'
import PageHeader from '@/components/common/PageHeader.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'
import StatusBadge from '@/components/common/StatusBadge.vue'
// AC-UX-065 (ADR-UX-16, docs/ui-ux/06 §5): xác nhận đi qua `notify.confirm()` — SSoT
// hộp thoại. `useNotify` đã được import sẵn ở trên cho luồng thông báo.
const toast = useToast()

const props = defineProps<{ name: string }>()

const CATEGORY_LABEL: Record<string, string> = {
  Legal: 'Pháp lý', Technical: 'Kỹ thuật', Certification: 'Kiểm định',
  Training: 'Đào tạo', QA: 'Chất lượng',
}

const router = useRouter()
const store = useImm05Store()
const notify = useNotify()

const doc = computed(() => store.currentDocument)
const loading = computed(() => store.loading)
// `error` giữ nhiệm vụ CŨ: CHUỖI lỗi dùng chung (kể cả lỗi hành động lưu/duyệt). Lỗi của
// LƯỢT NẠP đi ref RIÊNG và giữ NGUYÊN đối tượng ⇒ phân loại được kind (bẫy 13.9.7).
const error = ref<string | null>(null)
const loadError = ref<unknown>(null)
const { kind: loadKind, message: loadMsg } = useDetailAccess(() => loadError.value)
const rejectReason = ref('')
const showRejectInput = ref(false)
const actionLoading = ref(false)

// Edit mode
const isEditing = ref(false)
const editForm = reactive<Partial<AssetDocumentDetail>>({})
const saveError = ref<string | null>(null)

// Upload new version modal
const showUploadNewVersion = ref(false)

const canEdit = computed(() => ['Draft', 'Rejected'].includes(doc.value?.workflow_state ?? ''))

// ── Server-driven CTA gating (GATE-8 / LL-FE-51) ──────────────────────────────
// Nút CHUYỂN TRẠNG THÁI (Gửi duyệt/Phê duyệt/Từ chối/Gửi lại/Lưu trữ) gate theo
// `allowed_transitions` (BE _DOC_VALID_TRANSITIONS, SoT = fixture 'IMM-05 Document
// Workflow') + capability doc.approve — KHÔNG hardcode doc.workflow_state === 'X'
// (mirror PMWorkOrderDetailView / IncidentDetailView). Ground truth = SERVER →
// hết false-permissive (nút Phê duyệt/Từ chối hiện rồi bấm mới 403 khi thiếu quyền)
// và hết dead-gate. workflow_state === 'X' chỉ còn ở NHÃN hiển thị read-only.
const allowedTransitions = computed<string[]>(() => doc.value?.allowed_transitions ?? [])
const canApprove = computed<boolean>(() => doc.value?.can_approve === 1)

// BR-05-02: tài liệu không được xóa — chỉ lưu trữ. Trạng thái cuối → read-only.
const isTerminalState = computed(() =>
  ['Archived', 'Expired'].includes(doc.value?.workflow_state ?? ''),
)

// "Tải lên phiên bản mới" KHÔNG phải transition workflow (điều hướng tạo tài liệu
// phiên bản kế) → không có trong allowed_transitions; chỉ khả dụng khi doc đã
// Active/Expired. Tách computed để khối action template không còn bare
// workflow_state === trong điều kiện render nút.
const canUploadNewVersion = computed(() =>
  ['Active', 'Expired'].includes(doc.value?.workflow_state ?? ''),
)

async function load(): Promise<void> {
  loadError.value = null                         // INV-UX4-7 — xoá lỗi ở DÒNG ĐẦU
  error.value = null
  try {
    await store.fetchDocument(props.name)
  } catch (e: unknown) {
    loadError.value = e
    return
  }
  // `stores/imm05` NUỐT lỗi thành chuỗi ⇒ ưu tiên `lastApiError` (còn nguyên kind), chỉ
  // rơi về `new Error(chuỗi)` khi store không phơi đối tượng lỗi.
  if (store.error) loadError.value = store.lastApiError ?? new Error(store.error)
}

async function loadDocument(): Promise<void> {
  await load()
}

onMounted(load)

function startEditing(): void {
  if (!doc.value) return
  editForm.doc_number = doc.value.doc_number
  editForm.version = doc.value.version
  editForm.issued_date = doc.value.issued_date
  editForm.expiry_date = doc.value.expiry_date ?? ''
  editForm.issuing_authority = doc.value.issuing_authority ?? ''
  editForm.visibility = doc.value.visibility
  editForm.change_summary = doc.value.change_summary ?? ''
  editForm.notes = doc.value.notes ?? ''
  saveError.value = null
  isEditing.value = true
}

function cancelEditing(): void {
  isEditing.value = false
  saveError.value = null
}

async function saveEdits(): Promise<void> {
  if (!doc.value) return
  actionLoading.value = true
  saveError.value = null
  const payload: Partial<AssetDocumentDetail> = {
    doc_number: editForm.doc_number,
    version: editForm.version,
    issued_date: editForm.issued_date,
    expiry_date: editForm.expiry_date || undefined,
    issuing_authority: editForm.issuing_authority || undefined,
    visibility: editForm.visibility,
    change_summary: editForm.change_summary || undefined,
    notes: editForm.notes || undefined,
  }
  const res = await store.updateDocument(doc.value.name, payload)
  actionLoading.value = false
  if (res?.success) {
    isEditing.value = false
    notify.show({ code: MSG.IMM05_SUCCESS })
  } else {
    saveError.value = store.error ?? 'Lưu thất bại'
    notify.fromError(store.lastApiError)
  }
}

async function submitForReview(): Promise<void> {
  if (!doc.value) return
  if (!doc.value.file_attachment) {
    toast.warning('Vui lòng đính kèm file tài liệu trước khi gửi duyệt.')
    return
  }
  actionLoading.value = true
  try {
    await apiSubmitForReview(doc.value.name)
    await loadDocument()
    notify.show({ code: MSG.IMM05_SUCCESS })
  } catch (e: unknown) {
    notify.fromError(toApiError(e))
  } finally {
    actionLoading.value = false
  }
}

function bumpVersion(current: string | undefined): string {
  // "1.0" → "1.1", "2" → "2.1", "1.9" → "1.10". Fallback "1.0" → "1.1".
  if (!current) return '1.1'
  const m = /^(\d+)\.(\d+)$/.exec(current.trim())
  if (m) return `${m[1]}.${Number.parseInt(m[2], 10) + 1}`
  const n = Number.parseInt(current, 10)
  return Number.isFinite(n) ? `${n}.1` : '1.1'
}

function navigateToNewVersion(): void {
  if (!doc.value) return
  showUploadNewVersion.value = false
  router.push({
    path: '/documents/new',
    query: {
      asset: doc.value.asset_ref,
      doc_type_detail: doc.value.doc_type_detail,
      version: bumpVersion(doc.value.version),
    },
  })
}

interface ExpiryDisplay {
  cssClass: string
  suffix: string
}

const expiryDisplay = computed<ExpiryDisplay>(() => {
  const raw = doc.value?.expiry_date
  if (!raw) return { cssClass: 'text-gray-800', suffix: '' }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const expiry = new Date(raw)
  expiry.setHours(0, 0, 0, 0)
  const diffDays = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return { cssClass: 'text-red-600 font-semibold', suffix: 'Đã hết hạn' }
  if (diffDays <= 30) return { cssClass: 'text-orange-600 font-semibold', suffix: `(còn ${diffDays} ngày)` }
  if (diffDays <= 90) return { cssClass: 'text-yellow-600', suffix: `(còn ${diffDays} ngày)` }
  return { cssClass: 'text-gray-800', suffix: '' }
})

// Keep backward compat alias used by template
const expiryDateClass = computed(() => expiryDisplay.value.cssClass)

// "Lưu trữ" (Active) / "Hủy bỏ" (Draft) → Archived. NĐ98: chỉ lưu trữ, không xóa.
// Gate hiển thị nút = allowedTransitions.includes('Archived') && canApprove (dưới).
async function handleArchive(): Promise<void> {
  if (!doc.value) return
  const ok = await notify.confirm({
    title: 'Lưu trữ tài liệu',
    body: 'Lưu trữ tài liệu này theo NĐ98 (lưu trữ 10 năm, không thể xoá). Tiếp tục?',
    tone: 'error',
    confirmText: 'Lưu trữ',
  })
  if (!ok) return
  actionLoading.value = true
  try {
    await apiArchiveDocument(doc.value.name)
    await loadDocument()
    notify.show({ code: MSG.IMM05_SUCCESS })
  } catch (e: unknown) {
    notify.fromError(toApiError(e))
  } finally {
    actionLoading.value = false
  }
}

async function handleApprove(): Promise<void> {
  if (!doc.value) return
  const confirmed = await notify.confirm({
    title: 'Phê duyệt tài liệu',
    body: 'Phê duyệt tài liệu này sẽ tự động lưu trữ phiên bản cũ. Tiếp tục?',
    tone: 'warning',
    confirmText: 'Phê duyệt',
  })
  if (!confirmed) return
  actionLoading.value = true
  const ok = await store.approveDocument(doc.value.name)
  actionLoading.value = false
  if (ok) {
    notify.show({ code: MSG.IMM05_SUCCESS })
    await loadDocument()
  } else {
    notify.fromError(store.lastApiError)
  }
}

async function handleReject(): Promise<void> {
  if (!doc.value || !rejectReason.value.trim()) return
  actionLoading.value = true
  const ok = await store.rejectDocument(doc.value.name, rejectReason.value)
  actionLoading.value = false
  if (ok) {
    showRejectInput.value = false
    rejectReason.value = ''
    notify.show({ code: MSG.IMM05_SUCCESS })
    await loadDocument()
  } else {
    notify.fromError(store.lastApiError)
  }
}
</script>

<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadKind"
    :error-message="loadMsg"
    :doc="doc"
    entity-label="hồ sơ tài liệu"
    :record-id="props.name"
    back-label="Về danh sách hồ sơ"
    :skeleton-rows="8"
    @retry="load()"
    @back="router.push('/documents')">
    <template #title>
      <PageHeader
        :title="doc?.name ?? props.name"
        :subtitle="doc ? (doc.asset_name || doc.asset_ref) : 'Hồ sơ tài liệu'"
        :back-to="'/documents'"
        back-label="← Danh sách hồ sơ"
        :breadcrumb="[
          { label: 'IMM-05 · Hồ sơ', to: '/documents' },
          { label: 'Danh sách', to: '/documents' },
          { label: doc?.name ?? props.name },
        ]"
      >
        <template #actions>
          <StatusBadge v-if="doc" :state="doc.workflow_state" size="md" />
          <span
            v-if="doc?.is_exempt === 1"
            class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700"
          >Miễn NĐ98</span>
        </template>
      </PageHeader>
    </template>

    <!-- Document detail -->
    <template v-if="doc">
      <!-- Actions card — server-driven CTA: nút chuyển trạng thái gate theo
           (allowedTransitions BE + capability doc.approve), KHÔNG hardcode
           doc.workflow_state === 'X' (GATE-8 / LL-FE-51). Cụm nằm TRONG nhánh content
           của shell ⇒ 403/404 ⇒ 0 nút, đúng bằng CẤU TRÚC. -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-4" data-testid="doc-actions">
        <div class="flex flex-wrap gap-3">
          <!-- Phê duyệt (→ Active) — allowedTransitions + capability doc.approve -->
          <button
            v-if="allowedTransitions.includes('Active') && canApprove"
            class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            :disabled="actionLoading"
            @click="handleApprove"
          >
            Duyệt tài liệu
          </button>
          <!-- Từ chối (→ Rejected) — allowedTransitions + capability doc.approve -->
          <button
            v-if="allowedTransitions.includes('Rejected') && canApprove"
            class="px-4 py-2 border border-red-300 text-red-600 text-sm rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
            :disabled="actionLoading"
            @click="showRejectInput = !showRejectInput"
          >
            Từ chối
          </button>

          <!-- Edit button (Draft or Rejected, not already editing) -->
          <button
            v-if="canEdit && !isEditing"
            class="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 transition-colors"
            @click="startEditing"
          >
            Chỉnh sửa
          </button>

          <!-- Gửi duyệt (Draft) / Gửi lại (Rejected) → Pending Review — GỘP MỘT nút
               (06 §7.5): cùng transition (submitForReview), cùng đích Pending Review →
               gate allowedTransitions.includes('Pending Review'); NHÃN chọn theo state
               (display-only, cho phép), KHÔNG dùng workflow_state=== trong điều kiện
               render. -->
          <button
            v-if="allowedTransitions.includes('Pending Review') && !isEditing"
            class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            :disabled="actionLoading"
            @click="submitForReview"
          >
            {{ doc.workflow_state === 'Rejected' ? 'Gửi lại' : 'Gửi duyệt' }}
          </button>

          <!-- Tải lên phiên bản mới (Active/Expired) — điều hướng, KHÔNG transition -->
          <button
            v-if="canUploadNewVersion"
            class="px-4 py-2 border border-blue-300 text-blue-600 text-sm rounded-lg hover:bg-blue-50 transition-colors"
            @click="showUploadNewVersion = true"
          >
            Tải lên phiên bản mới
          </button>
          <!-- Lưu trữ (Active) / Hủy bỏ (Draft) → Archived — allowedTransitions +
               capability doc.approve (NĐ98). workflow_state === 'Draft' CHỈ để chọn
               NHÃN hiển thị, KHÔNG quyết định render nút. -->
          <button
            v-if="allowedTransitions.includes('Archived') && canApprove && !isEditing"
            class="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            :disabled="actionLoading"
            @click="handleArchive"
          >
            {{ doc.workflow_state === 'Draft' ? 'Hủy bỏ' : 'Lưu trữ' }}
          </button>

          <!-- BR-05-02: terminal state — read-only, không cho xóa -->
          <p
            v-if="isTerminalState"
            class="text-sm text-gray-500 italic"
          >
            Tài liệu ở trạng thái cuối ({{ doc.workflow_state === 'Expired' ? 'Đã hết hạn' : 'Đã lưu trữ' }}) — chỉ xem. Theo NĐ98 (lưu trữ 10 năm) tài liệu không được phép xóa, chỉ lưu trữ.
          </p>
        </div>

        <!-- Reject reason input -->
        <div v-if="showRejectInput" class="mt-3">
          <textarea
            v-model="rejectReason"
            rows="2"
            placeholder="Nhập lý do từ chối..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
          />
          <button
            class="mt-2 px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            :disabled="!rejectReason.trim() || actionLoading"
            @click="handleReject"
          >
            Xác nhận Từ chối
          </button>
        </div>
      </div>

      <!-- Metadata card -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Thông tin tài liệu</h2>

        <!-- Edit error -->
        <div v-if="saveError" class="mb-4 p-3 bg-red-50 rounded-lg border border-red-100">
          <p class="text-sm text-red-600">{{ saveError }}</p>
        </div>

        <!-- Save / Cancel buttons (edit mode) -->
        <div v-if="isEditing" class="flex gap-3 mb-4">
          <button
            class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            :disabled="actionLoading"
            @click="saveEdits"
          >
            <span v-if="actionLoading">Đang lưu...</span>
            <span v-else>Lưu</span>
          </button>
          <button
            class="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
            :disabled="actionLoading"
            @click="cancelEditing"
          >
            Hủy
          </button>
        </div>

        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Nhóm</dt>
            <dd class="text-gray-800">{{ doc?.doc_category ? (CATEGORY_LABEL[doc.doc_category] ?? doc.doc_category) : '—' }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Loại tài liệu</dt>
            <dd class="text-gray-800">{{ doc.doc_type_detail }}</dd>
          </div>

          <!-- Số tài liệu: editable -->
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Số tài liệu</dt>
            <dd v-if="!isEditing" class="text-gray-800">{{ doc.doc_number || '—' }}</dd>
            <dd v-else>
              <input
                v-model="editForm.doc_number"
                type="text"
                class="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </dd>
          </div>

          <!-- Phiên bản: editable -->
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Phiên bản</dt>
            <dd v-if="!isEditing" class="text-gray-800">{{ doc.version }}</dd>
            <dd v-else>
              <input
                v-model="editForm.version"
                type="text"
                class="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </dd>
          </div>

          <!-- Ngày phát hành: editable -->
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Ngày phát hành</dt>
            <dd v-if="!isEditing" class="text-gray-800">{{ formatDate(doc.issued_date) }}</dd>
            <dd v-else>
              <DateInput v-model="editForm.issued_date" class="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </dd>
          </div>

          <!-- Ngày hết hạn: editable -->
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Ngày hết hạn</dt>
            <dd v-if="!isEditing" :class="expiryDateClass">
              {{ formatDate(doc.expiry_date) }}
              <span v-if="expiryDisplay.suffix" class="text-xs ml-1">{{ expiryDisplay.suffix }}</span>
            </dd>
            <dd v-else>
              <DateInput v-model="editForm.expiry_date" class="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </dd>
          </div>

          <!-- Cơ quan cấp: editable -->
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Cơ quan cấp</dt>
            <dd v-if="!isEditing" class="text-gray-800">{{ doc.issuing_authority || '—' }}</dd>
            <dd v-else>
              <input
                v-model="editForm.issuing_authority"
                type="text"
                class="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="Bộ Y tế / Cục Quản lý Dược..."
              />
            </dd>
          </div>

          <!-- Hiển thị: editable -->
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Hiển thị</dt>
            <dd v-if="!isEditing" class="text-gray-800">{{ doc.visibility === 'Public' ? 'Công khai' : 'Nội bộ' }}</dd>
            <dd v-else>
              <select
                v-model="editForm.visibility"
                class="w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="Public">Công khai (Public)</option>
                <option value="Internal_Only">Nội bộ (Internal Only)</option>
              </select>
            </dd>
          </div>

          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Người duyệt</dt>
            <dd class="text-gray-800">{{ doc.approved_by || '—' }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Ngày duyệt</dt>
            <dd class="text-gray-800">{{ formatDate(doc.approval_date) }}</dd>
          </div>

          <div v-if="doc.source_commissioning">
            <dt class="text-gray-400 font-medium mb-0.5">Phiếu commissioning</dt>
            <dd class="text-gray-800">{{ doc.source_commissioning }}</dd>
          </div>
          <div v-if="doc.is_exempt">
            <dt class="text-gray-400 font-medium mb-0.5">Miễn đăng ký NĐ98</dt>
            <dd class="text-yellow-700 font-medium">Miễn đăng ký</dd>
          </div>
        </dl>

        <!-- Change summary: always visible in view mode, editable when editing -->
        <div class="mt-4">
          <p class="text-xs font-semibold text-gray-500 mb-1">Tóm tắt thay đổi</p>
          <div v-if="!isEditing" class="p-3 bg-gray-50 rounded-lg">
            <p class="text-sm text-gray-700">{{ doc.change_summary || '—' }}</p>
          </div>
          <textarea
            v-else
            v-model="editForm.change_summary"
            rows="2"
            placeholder="Tóm tắt nội dung thay đổi so với phiên bản trước..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>

        <div v-if="doc.rejection_reason" class="mt-4 p-3 bg-red-50 rounded-lg border border-red-100">
          <p class="text-xs font-semibold text-red-700 mb-1">Lý do từ chối</p>
          <p class="text-sm text-red-600">{{ doc.rejection_reason }}</p>
        </div>

        <!-- Notes: editable -->
        <div v-if="isEditing || doc.notes" class="mt-4">
          <p class="text-xs font-semibold text-gray-500 mb-1">Ghi chú</p>
          <div v-if="!isEditing" class="p-3 bg-gray-50 rounded-lg">
            <p class="text-sm text-gray-700">{{ doc.notes }}</p>
          </div>
          <textarea
            v-else
            v-model="editForm.notes"
            rows="3"
            placeholder="Ghi chú thêm..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>

      <!-- File attachment -->
      <div v-if="doc.file_attachment" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Tệp đính kèm</h2>
        <a
          :href="doc.file_attachment"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm hover:bg-blue-100 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
          </svg>
          Xem tệp đính kèm
        </a>
      </div>

      <!-- Upload new version modal -->
      <div
        v-if="showUploadNewVersion"
        class="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50"
        @click.self="showUploadNewVersion = false"
      >
        <div class="bg-white rounded-xl shadow-lg p-6 w-full max-w-md mx-4">
          <h3 class="text-base font-semibold text-gray-800 mb-2">Tải lên phiên bản mới</h3>
          <p class="text-sm text-gray-500 mb-4">
            Bạn sẽ được chuyển sang form tạo tài liệu mới với thông tin thiết bị và loại tài liệu được điền sẵn.
          </p>
          <p class="text-sm text-gray-700 mb-1"><span class="font-medium">Thiết bị:</span> {{ doc.asset_name || doc.asset_ref }}</p>
          <p class="text-sm text-gray-700 mb-4"><span class="font-medium">Loại tài liệu:</span> {{ doc.doc_type_detail }}</p>
          <div class="flex justify-end gap-3">
            <button
              class="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
              @click="showUploadNewVersion = false"
            >
              Hủy
            </button>
            <button
              class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              @click="navigateToNewVersion"
            >
              Tiếp tục
            </button>
          </div>
        </div>
      </div>
    </template>
  </DetailPageShell>
</template>
