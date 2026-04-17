<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDocument, approveDocument, rejectDocument } from '@/api/imm05'
import type { AssetDocumentDetail } from '@/api/imm05'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const props = defineProps<{ name: string }>()

const router = useRouter()

const doc = ref<AssetDocumentDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const rejectReason = ref('')
const showRejectInput = ref(false)
const actionLoading = ref(false)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await getDocument(props.name)
    if (res.success) {
      doc.value = res.data
    } else {
      error.value = res.error ?? 'Không tải được tài liệu'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function goBack(): void {
  router.push('/documents')
}

function formatDate(date: string | null | undefined): string {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('vi-VN')
}

function stateLabel(state: string): string {
  const map: Record<string, string> = {
    Draft: 'Draft',
    Pending_Review: 'Chờ duyệt',
    Active: 'Active',
    Expired: 'Hết hạn',
    Archived: 'Lưu trữ',
    Rejected: 'Từ chối',
  }
  return map[state] ?? state
}

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
  try {
    const res = await approveDocument(doc.value.name)
    if (res.success) {
      doc.value.workflow_state = res.data.new_state
    }
  } finally {
    actionLoading.value = false
  }
}

async function handleReject(): Promise<void> {
  if (!doc.value || !rejectReason.value.trim()) return
  actionLoading.value = true
  try {
    const res = await rejectDocument(doc.value.name, rejectReason.value)
    if (res.success) {
      doc.value.workflow_state = res.data.new_state
      showRejectInput.value = false
      rejectReason.value = ''
    }
  } finally {
    actionLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
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
            <p class="text-gray-500 text-sm mt-1">{{ doc.asset_ref }}</p>
          </div>
          <span
            :class="[
              'shrink-0 inline-block px-3 py-1 rounded-full text-xs font-semibold',
              stateBadgeClass(doc.workflow_state),
            ]"
          >
            {{ stateLabel(doc.workflow_state) }}
          </span>
        </div>

        <!-- Approve / Reject actions -->
        <div v-if="doc.workflow_state === 'Pending_Review'" class="mt-5 pt-4 border-t border-gray-100">
          <div class="flex gap-3 flex-wrap">
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
          </div>
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
      </div>

      <!-- Metadata card -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Thông tin tài liệu</h2>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4 text-sm">
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Nhóm</dt>
            <dd class="text-gray-800">{{ doc.doc_category }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Loại tài liệu</dt>
            <dd class="text-gray-800">{{ doc.doc_type_detail }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Số tài liệu</dt>
            <dd class="text-gray-800">{{ doc.doc_number || '—' }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Phiên bản</dt>
            <dd class="text-gray-800">{{ doc.version }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Ngày phát hành</dt>
            <dd class="text-gray-800">{{ formatDate(doc.issued_date) }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Ngày hết hạn</dt>
            <dd :class="['font-medium', doc.days_until_expiry !== null && doc.days_until_expiry <= 0 ? 'text-red-600' : doc.days_until_expiry !== null && doc.days_until_expiry <= 30 ? 'text-yellow-600' : 'text-gray-800']">
              {{ formatDate(doc.expiry_date) }}
              <span v-if="doc.days_until_expiry !== null" class="text-xs text-gray-400 ml-1">({{ doc.days_until_expiry }}d)</span>
            </dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Cơ quan cấp</dt>
            <dd class="text-gray-800">{{ doc.issuing_authority || '—' }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Người duyệt</dt>
            <dd class="text-gray-800">{{ doc.approved_by || '—' }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Ngày duyệt</dt>
            <dd class="text-gray-800">{{ formatDate(doc.approval_date) }}</dd>
          </div>
          <div>
            <dt class="text-gray-400 font-medium mb-0.5">Hiển thị</dt>
            <dd class="text-gray-800">{{ doc.visibility === 'Public' ? 'Công khai' : 'Nội bộ' }}</dd>
          </div>
          <div v-if="doc.source_commissioning">
            <dt class="text-gray-400 font-medium mb-0.5">Phiếu commissioning</dt>
            <dd class="text-gray-800">{{ doc.source_commissioning }}</dd>
          </div>
          <div v-if="doc.is_exempt">
            <dt class="text-gray-400 font-medium mb-0.5">Miễn đăng ký NĐ98</dt>
            <dd class="text-yellow-700 font-medium">Exempt</dd>
          </div>
        </dl>

        <div v-if="doc.rejection_reason" class="mt-4 p-3 bg-red-50 rounded-lg border border-red-100">
          <p class="text-xs font-semibold text-red-700 mb-1">Lý do từ chối</p>
          <p class="text-sm text-red-600">{{ doc.rejection_reason }}</p>
        </div>

        <div v-if="doc.notes" class="mt-4 p-3 bg-gray-50 rounded-lg">
          <p class="text-xs font-semibold text-gray-500 mb-1">Ghi chú</p>
          <p class="text-sm text-gray-700">{{ doc.notes }}</p>
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
    </template>
  </div>
</template>
