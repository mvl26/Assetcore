<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import DateInput from '@/components/common/DateInput.vue'
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useImm05Store } from '@/stores/imm05Store'
import type { AssetDocumentDetail } from '@/api/imm05'
import { stateLabel, formatDate } from '@/utils/docUtils'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
const toast = useToast()

const props = defineProps<{ name: string }>()

const router = useRouter()
const store = useImm05Store()

const doc = computed(() => store.currentDocument)
const loading = computed(() => store.loading)
const error = ref<string | null>(null)
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

async function load(): Promise<void> {
  error.value = null
  await store.fetchDocument(props.name)
  if (store.error) error.value = store.error
}

async function loadDocument(): Promise<void> {
  await load()
}

onMounted(load)

function goBack(): void {
  router.push('/documents')
}

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
  } else {
    saveError.value = store.error ?? 'Lưu thất bại'
  }
}

function resubmit(): void {
  startEditing()
}

async function transitionState(name: string, action: string) {
  try {
    const { frappePost } = await import('@/api/helpers')
    const res = await frappePost('frappe.model.workflow.apply_workflow', {
      doc: { doctype: 'Asset Document', name },
      action,
    })
    return res
  } catch (e) {
    console.error(e)
    return null
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
    const res = await transitionState(doc.value.name, 'Gửi duyệt')
    if (res) await loadDocument()
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
  if (diffDays <= 0) return { cssClass: 'text-red-600 font-semibold', suffix: '⚠ Đã hết hạn' }
  if (diffDays <= 30) return { cssClass: 'text-orange-600 font-semibold', suffix: `(còn ${diffDays} ngày)` }
  if (diffDays <= 90) return { cssClass: 'text-yellow-600', suffix: `(còn ${diffDays} ngày)` }
  return { cssClass: 'text-gray-800', suffix: '' }
})

// Keep backward compat alias used by template
const expiryDateClass = computed(() => expiryDisplay.value.cssClass)

function stateBadgeClass(state: string): string {
  const map: Record<string, string> = {
    Active: 'bg-green-100 text-green-800',
    Draft: 'bg-gray-100 text-gray-700',
    Pending_Review: 'bg-yellow-100 text-yellow-800',
    Expired: 'bg-red-100 text-red-800',
    Archived: 'bg-gray-100 text-gray-500',
    Rejected: 'bg-pink-100 text-pink-800',
  }
  return map[state] ?? 'bg-gray-100 text-gray-700'
}

async function handleApprove(): Promise<void> {
  if (!doc.value) return
  if (!confirm(`Xác nhận DUYỆT tài liệu ${doc.value.name}?`)) return
  actionLoading.value = true
  await store.approveDocument(doc.value.name)
  actionLoading.value = false
  await loadDocument()
}

async function handleReject(): Promise<void> {
  if (!doc.value || !rejectReason.value.trim()) return
  actionLoading.value = true
  const ok = await store.rejectDocument(doc.value.name, rejectReason.value)
  actionLoading.value = false
  if (ok) {
    showRejectInput.value = false
    rejectReason.value = ''
    await loadDocument()
  }
}
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Back button -->
    <button
      class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
      @click="goBack"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
      </svg>
      Quay lại danh sách
    </button>

    <!-- Loading skeleton -->
    <div v-if="loading" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <SkeletonLoader :rows="8" :cols="2" />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="bg-white rounded-xl shadow-sm border border-red-200 p-6 text-center">
      <svg class="w-12 h-12 text-red-400 mx-auto mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      <p class="text-red-600 font-medium mb-1">Không thể tải tài liệu</p>
      <p class="text-gray-500 text-sm mb-4">{{ error }}</p>
      <button
        class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors"
        @click="load"
      >
        Thử lại
      </button>
    </div>

    <!-- Document detail -->
    <template v-else-if="doc">
      <!-- Header card -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-4">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h1 class="text-xl font-bold text-gray-900 truncate">{{ doc.name }}</h1>
            <p class="text-gray-500 text-sm mt-1">
              {{ doc.asset_name || doc.asset_ref }}
              <span v-if="doc.asset_name" class="text-xs text-gray-400 font-mono ml-2">{{ doc.asset_ref }}</span>
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span
              :class="[
                'inline-block px-3 py-1 rounded-full text-xs font-semibold',
                stateBadgeClass(doc.workflow_state),
              ]"
            >
              {{ stateLabel(doc.workflow_state) }}
            </span>
            <span
              v-if="doc.is_exempt === 1"
              class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700"
            >
              Miễn NĐ98
            </span>
          </div>
        </div>

        <!-- Action buttons row -->
        <div class="mt-5 pt-4 border-t border-gray-100 flex flex-wrap gap-3">
<!-- Approve / Reject actions (Pending_Review) -->
          <template v-if="doc.workflow_state === 'Pending_Review'">
            <button
              class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              :disabled="actionLoading"
              @click="handleApprove"
            >
              Duyệt tài liệu
            </button>
            <button
              class="px-4 py-2 border border-red-300 text-red-600 text-sm rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
              :disabled="actionLoading"
              @click="showRejectInput = !showRejectInput"
            >
              Từ chối
            </button>
          </template>

          <!-- Edit button (Draft or Rejected, not already editing) -->
          <button
            v-if="canEdit && !isEditing"
            class="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 transition-colors"
            @click="startEditing"
          >
            Chỉnh sửa
          </button>

          <!-- Gửi duyệt button (Draft, not editing) -->
          <button
            v-if="doc.workflow_state === 'Draft' && !isEditing"
            class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            :disabled="actionLoading"
            @click="submitForReview"
          >
            Gửi duyệt
          </button>

          <!-- Chỉnh sửa và gửi lại (Rejected) -->
          <button
            v-if="doc.workflow_state === 'Rejected' && !isEditing"
            class="px-4 py-2 border border-orange-300 text-orange-600 text-sm rounded-lg hover:bg-orange-50 transition-colors"
            @click="resubmit"
          >
            Chỉnh sửa và gửi lại
          </button>

          <!-- Upload phiên bản mới (Active or Expired) -->
          <button
            v-if="doc.workflow_state === 'Active' || doc.workflow_state === 'Expired'"
            class="px-4 py-2 border border-blue-300 text-blue-600 text-sm rounded-lg hover:bg-blue-50 transition-colors"
            @click="showUploadNewVersion = true"
          >
            Upload phiên bản mới
          </button>
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
            <dd class="text-gray-800">{{ doc.doc_category }}</dd>
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
          <h3 class="text-base font-semibold text-gray-800 mb-2">Upload phiên bản mới</h3>
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
  </div>
</template>
