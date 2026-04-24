<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useImm14Store } from '@/stores/imm14'
import { useRouter } from 'vue-router'

const props = defineProps<{ id: string }>()
const store = useImm14Store()
const router = useRouter()
const activeTab = ref<'info' | 'documents'>('info')
const submitting = ref(false)

// Modal state
const showVerifyModal = ref(false)
const showApproveModal = ref(false)
const showFinalizeConfirm = ref(false)

// Modal forms
const verifiedBy = ref('')
const verifyNotes = ref('')
const approvedBy = ref('')
const approveNotes = ref('')

const rec = computed(() => store.currentArchive)

const STATUSES: Record<string, string> = {
  'Draft': 'Nháp',
  'Compiling': 'Đang tổng hợp',
  'Pending Verification': 'Chờ xác minh QA',
  'Pending Approval': 'Chờ phê duyệt',
  'Finalized': 'Đã phê duyệt',
  'Archived': 'Đã lưu trữ',
}

function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    'Draft': 'bg-blue-100 text-blue-700',
    'Compiling': 'bg-blue-100 text-blue-700',
    'Pending Verification': 'bg-yellow-100 text-yellow-700',
    'Pending Approval': 'bg-yellow-100 text-yellow-700',
    'Finalized': 'bg-orange-100 text-orange-700',
    'Archived': 'bg-green-100 text-green-700',
  }
  return map[status] ?? 'bg-slate-100 text-slate-600'
}

function docStatusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    'Included': 'bg-green-100 text-green-700',
    'Missing': 'bg-red-100 text-red-700',
    'Waived': 'bg-slate-100 text-slate-500',
  }
  return map[status] ?? 'bg-slate-100 text-slate-600'
}

const missingDocs = computed(() =>
  (rec.value?.documents ?? []).filter(d => d.archive_status === 'Missing').length
)

async function doCompile() {
  if (!rec.value) return
  submitting.value = true
  await store.doCompileHistory(rec.value.name)
  submitting.value = false
}

async function doVerify() {
  if (!rec.value) return
  submitting.value = true
  const ok = await store.doVerifyArchive({
    name: rec.value.name,
    verified_by: verifiedBy.value || undefined,
    notes: verifyNotes.value,
  })
  submitting.value = false
  if (ok) showVerifyModal.value = false
}

async function doApprove() {
  if (!rec.value) return
  submitting.value = true
  const ok = await store.doApproveArchive({
    name: rec.value.name,
    approved_by: approvedBy.value || undefined,
    notes: approveNotes.value,
  })
  submitting.value = false
  if (ok) showApproveModal.value = false
}

async function doFinalize() {
  if (!rec.value) return
  submitting.value = true
  await store.doFinalizeArchive(rec.value.name)
  submitting.value = false
  showFinalizeConfirm.value = false
}

onMounted(() => store.fetchArchive(props.id))
</script>

<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-5">
      <button class="text-slate-400 hover:text-slate-600" @click="router.back()">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
      <div class="flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-mono text-lg font-bold text-slate-900">{{ rec?.name }}</span>
          <span v-if="rec" :class="['px-2.5 py-1 rounded-full text-xs font-semibold', statusBadgeClass(rec.status)]">
            {{ STATUSES[rec.status] ?? rec.status }}
          </span>
          <span v-if="missingDocs > 0" class="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">
            ⚠ {{ missingDocs }} tài liệu thiếu
          </span>
        </div>
        <div class="text-sm text-slate-500 mt-0.5">{{ rec?.asset_name || rec?.asset }}</div>
      </div>
    </div>

    <div v-if="store.loading" class="text-center py-12 text-slate-400">Đang tải...</div>
    <div v-else-if="store.error && !rec" class="card p-6 text-center text-red-600">{{ store.error }}</div>

    <div v-else-if="rec" class="grid md:grid-cols-5 gap-6">
      <!-- LEFT: Main content -->
      <div class="md:col-span-3 space-y-5">

        <!-- Tabs -->
        <div class="flex gap-0 border-b border-slate-200">
          <button
            v-for="tab in [['info', 'Thông tin'], ['documents', 'Tài liệu']]"
            :key="tab[0]"
            :class="['px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab[0]
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = tab[0] as any"
          >
            {{ tab[1] }}
            <span v-if="tab[0] === 'documents'" class="ml-1 text-xs opacity-60">({{ rec.documents?.length ?? 0 }})</span>
          </button>
        </div>

        <!-- Tab: Thông tin -->
        <div v-show="activeTab === 'info'" class="space-y-4">

          <!-- Asset info -->
          <div class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Thông tin Thiết bị</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div class="col-span-2">
                <span class="text-slate-500">Thiết bị:</span>
                <span class="font-semibold ml-1">{{ rec.asset_name || rec.asset }}</span>
                <span class="ml-2 font-mono text-xs text-slate-400">{{ rec.asset }}</span>
              </div>
              <div v-if="rec.decommission_request">
                <span class="text-slate-500">Phiếu IMM-13:</span>
                <router-link :to="`/decommission/${rec.decommission_request}`" class="ml-1 text-blue-600 hover:underline font-mono text-xs">
                  {{ rec.decommission_request }}
                </router-link>
              </div>
            </div>
          </div>

          <!-- Archive info -->
          <div class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Thông tin Lưu trữ</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div><span class="text-slate-500">Ngày lưu trữ:</span> <span class="font-medium">{{ rec.archive_date || '—' }}</span></div>
              <div><span class="text-slate-500">Số năm lưu trữ:</span> <span class="font-medium">{{ rec.retention_years }} năm</span></div>
              <div><span class="text-slate-500">Ngày hết hạn:</span> <span class="font-medium">{{ rec.release_date || '—' }}</span></div>
              <div><span class="text-slate-500">Vị trí lưu trữ:</span> <span class="font-medium">{{ rec.storage_location || '—' }}</span></div>
              <div><span class="text-slate-500">Người lưu trữ:</span> <span>{{ rec.archived_by || '—' }}</span></div>
            </div>
          </div>

          <!-- 4-way reconciliation -->
          <div class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Đối soát 4 chiều</h2>
            <div class="grid grid-cols-2 gap-3 text-sm mb-3">
              <div class="flex items-center gap-2">
                <span :class="['w-4 h-4 rounded flex items-center justify-center text-xs font-bold',
                  rec.reconcile_cmms ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-400']">
                  {{ rec.reconcile_cmms ? '✓' : '–' }}
                </span>
                <span class="text-slate-700">CMMS</span>
              </div>
              <div class="flex items-center gap-2">
                <span :class="['w-4 h-4 rounded flex items-center justify-center text-xs font-bold',
                  rec.reconcile_inventory ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-400']">
                  {{ rec.reconcile_inventory ? '✓' : '–' }}
                </span>
                <span class="text-slate-700">Kho</span>
              </div>
              <div class="flex items-center gap-2">
                <span :class="['w-4 h-4 rounded flex items-center justify-center text-xs font-bold',
                  rec.reconcile_finance ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-400']">
                  {{ rec.reconcile_finance ? '✓' : '–' }}
                </span>
                <span class="text-slate-700">Kế toán</span>
              </div>
              <div class="flex items-center gap-2">
                <span :class="['w-4 h-4 rounded flex items-center justify-center text-xs font-bold',
                  rec.reconcile_legal ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-400']">
                  {{ rec.reconcile_legal ? '✓' : '–' }}
                </span>
                <span class="text-slate-700">Hồ sơ pháp lý</span>
              </div>
            </div>
            <div v-if="rec.reconciliation_notes" class="text-xs text-slate-500 bg-slate-50 p-2 rounded">
              {{ rec.reconciliation_notes }}
            </div>
          </div>

          <!-- QA Verification -->
          <div v-if="rec.qa_verified_by" class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Xác minh QA</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div><span class="text-slate-500">QA Officer:</span> <span class="font-medium">{{ rec.qa_verified_by }}</span></div>
              <div><span class="text-slate-500">Ngày xác minh:</span> <span>{{ rec.qa_verification_date || '—' }}</span></div>
              <div v-if="rec.qa_verification_notes" class="col-span-2">
                <span class="text-slate-500">Ghi chú:</span>
                <p class="mt-1 text-slate-700">{{ rec.qa_verification_notes }}</p>
              </div>
            </div>
          </div>

          <!-- HTM Approval -->
          <div v-if="rec.approved_by" class="bg-white rounded-xl shadow-sm border p-5">
            <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Phê duyệt HTM Manager</h2>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div><span class="text-slate-500">Người phê duyệt:</span> <span class="font-medium">{{ rec.approved_by }}</span></div>
              <div><span class="text-slate-500">Ngày phê duyệt:</span> <span>{{ rec.approval_date || '—' }}</span></div>
              <div v-if="rec.approval_notes" class="col-span-2">
                <span class="text-slate-500">Ghi chú:</span>
                <p class="mt-1 text-slate-700">{{ rec.approval_notes }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab: Documents -->
        <div v-show="activeTab === 'documents'">
          <div class="bg-white rounded-xl shadow-sm border overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <span class="text-sm font-medium text-slate-700">
                {{ rec.documents?.length ?? 0 }} tài liệu
                <span v-if="missingDocs > 0" class="ml-2 text-red-600">({{ missingDocs }} thiếu)</span>
              </span>
            </div>
            <div v-if="!rec.documents?.length" class="py-8 text-center text-slate-400">
              <p class="text-sm">Chưa có tài liệu. Nhấn "Tổng hợp tài liệu" để bắt đầu.</p>
            </div>
            <table v-else class="min-w-full divide-y divide-slate-100 text-sm">
              <thead>
                <tr>
                  <th class="table-header">Loại</th>
                  <th class="table-header">Mã tài liệu</th>
                  <th class="table-header">Ngày</th>
                  <th class="table-header">Trạng thái</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="doc in rec.documents" :key="doc.idx" class="hover:bg-slate-50">
                  <td class="table-cell font-medium">{{ doc.document_type }}</td>
                  <td class="table-cell font-mono text-xs text-slate-600">{{ doc.document_name || '—' }}</td>
                  <td class="table-cell text-slate-500">{{ doc.document_date || '—' }}</td>
                  <td class="table-cell">
                    <span :class="['px-2 py-0.5 rounded-full text-xs font-medium', docStatusBadgeClass(doc.archive_status)]">
                      {{ doc.archive_status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- RIGHT: Actions -->
      <div class="md:col-span-2 space-y-4">
        <div class="bg-white rounded-xl shadow-sm border p-5">
          <h2 class="font-semibold text-slate-700 mb-3 text-sm">Thao tác</h2>
          <div class="space-y-2">

            <!-- Draft or Compiling: compile button -->
            <template v-if="['Draft', 'Compiling'].includes(rec.status)">
              <button
                :disabled="submitting"
                class="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                @click="doCompile"
              >
                {{ submitting ? 'Đang tổng hợp...' : 'Tổng hợp tài liệu tự động' }}
              </button>
            </template>

            <!-- After compile (Compiling state): can send for verification -->
            <template v-if="rec.status === 'Compiling'">
              <button
                class="w-full px-4 py-2.5 border border-purple-300 text-purple-600 rounded-lg text-sm font-medium hover:bg-purple-50 transition-colors"
                @click="showVerifyModal = true"
              >
                Gửi xác minh QA
              </button>
            </template>

            <!-- Pending Verification: QA verifies -->
            <template v-if="rec.status === 'Pending Verification'">
              <button
                class="w-full px-4 py-2.5 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
                @click="showVerifyModal = true"
              >
                Xác minh đầy đủ hồ sơ
              </button>
            </template>

            <!-- Pending Approval: HTM Manager approves -->
            <template v-if="rec.status === 'Pending Approval'">
              <button
                class="w-full px-4 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                @click="showApproveModal = true"
              >
                Phê duyệt hồ sơ
              </button>
            </template>

            <!-- Finalized: lock permanently -->
            <template v-if="rec.status === 'Finalized'">
              <button
                :disabled="submitting"
                class="w-full px-4 py-2.5 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 disabled:opacity-50 transition-colors"
                @click="showFinalizeConfirm = true"
              >
                Khóa hồ sơ vĩnh viễn
              </button>
            </template>

            <!-- Archived: terminal -->
            <div v-if="rec.status === 'Archived'" class="text-center py-2 text-green-600 font-semibold text-sm">
              ✓ Hồ sơ đã lưu trữ vĩnh viễn
            </div>
          </div>
        </div>

        <!-- Stats -->
        <div class="bg-white rounded-xl shadow-sm border p-4 text-sm space-y-2">
          <div class="flex justify-between text-slate-500">
            <span>Tổng tài liệu:</span>
            <span class="font-medium text-slate-900">{{ rec.total_documents_archived }}</span>
          </div>
          <div v-if="missingDocs > 0" class="flex justify-between text-red-500">
            <span>Thiếu:</span>
            <span class="font-medium">{{ missingDocs }}</span>
          </div>
          <div class="flex justify-between text-slate-500">
            <span>Ngày lưu trữ:</span>
            <span class="font-medium text-slate-900">{{ rec.archive_date || '—' }}</span>
          </div>
          <div class="flex justify-between text-slate-500">
            <span>Hết hạn:</span>
            <span class="font-medium text-slate-900">{{ rec.release_date || '—' }}</span>
          </div>
        </div>

        <div v-if="store.error" class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {{ store.error }}
        </div>
      </div>
    </div>

    <!-- Modal: Verify -->
    <Transition name="fade">
    <div v-if="showVerifyModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg mb-4">Xác minh tính đầy đủ hồ sơ</h3>
        <div class="space-y-3 mb-5">
          <div>
            <label class="block text-sm text-slate-600 mb-1">Email QA Officer</label>
            <input v-model="verifiedBy" type="text" class="form-input w-full" placeholder="qa@hospital.vn" />
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Ghi chú xác minh</label>
            <textarea v-model="verifyNotes" rows="3" class="form-input w-full" placeholder="Nhận xét về tính đầy đủ..." />
          </div>
        </div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showVerifyModal = false">Hủy</button>
          <button :disabled="submitting" class="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doVerify">
            {{ submitting ? 'Đang xác minh...' : 'Xác minh' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>

    <!-- Modal: Approve -->
    <Transition name="fade">
    <div v-if="showApproveModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="font-bold text-lg mb-4">Phê duyệt Hồ sơ Lưu trữ</h3>
        <div class="space-y-3 mb-5">
          <div>
            <label class="block text-sm text-slate-600 mb-1">Email HTM Manager</label>
            <input v-model="approvedBy" type="text" class="form-input w-full" placeholder="manager@hospital.vn" />
          </div>
          <div>
            <label class="block text-sm text-slate-600 mb-1">Ghi chú phê duyệt</label>
            <textarea v-model="approveNotes" rows="3" class="form-input w-full" placeholder="Ghi chú..." />
          </div>
        </div>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showApproveModal = false">Hủy</button>
          <button :disabled="submitting" class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50" @click="doApprove">
            {{ submitting ? 'Đang phê duyệt...' : 'Phê duyệt' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>

    <!-- Finalize Confirm Dialog -->
    <Transition name="fade">
    <div v-if="showFinalizeConfirm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 w-full max-w-sm mx-4 shadow-2xl">
        <h3 class="font-bold text-lg text-orange-700 mb-2">Khóa hồ sơ vĩnh viễn</h3>
        <p class="text-sm text-slate-600 mb-5">
          Hành động này sẽ khóa hồ sơ và đặt thiết bị sang trạng thái <strong>Archived</strong>.
          Sau khi khóa, không thể thay đổi hồ sơ này. Bạn có chắc chắn?
        </p>
        <div class="flex justify-end gap-3">
          <button class="px-4 py-2 border border-slate-300 rounded-lg text-sm" @click="showFinalizeConfirm = false">Hủy</button>
          <button
            :disabled="submitting"
            class="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm font-medium disabled:opacity-50"
            @click="doFinalize"
          >
            {{ submitting ? 'Đang xử lý...' : 'Xác nhận khóa' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
