<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import VendorScoringTable from '@/components/common/VendorScoringTable.vue'
import { formatDate } from '@/utils/docUtils'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store  = useImm03Store()

const doc = computed(() => store.currentVe)

// ─── Tech approval modal ──────────────────────────────────────────────────────
const showTechModal  = ref(false)
const techNotes      = ref('')
const actionError    = ref<string | null>(null)

async function handleApproveTech() {
  actionError.value = null
  const ok = await store.approveTech(props.id, techNotes.value || undefined)
  if (ok) {
    showTechModal.value = false
    techNotes.value = ''
  } else {
    actionError.value = store.veError
  }
}

// ─── Finance approval modal ───────────────────────────────────────────────────
const showFinanceModal      = ref(false)
const financeForm = ref({
  recommended_vendor: '',
  selection_justification: '',
  committee_members: '',
})
const financeError  = ref<string | null>(null)
const createdPors   = ref<string[]>([])

function openFinanceModal() {
  financeForm.value = {
    recommended_vendor: '',
    selection_justification: '',
    committee_members: '',
  }
  financeError.value = null
  createdPors.value = []
  showFinanceModal.value = true
}

async function handleApproveFinance() {
  financeError.value = null
  if (!financeForm.value.recommended_vendor) {
    financeError.value = 'Vui lòng chọn nhà cung cấp được đề xuất'
    return
  }
  const result = await store.approveFinance({
    name: props.id,
    recommended_vendor: financeForm.value.recommended_vendor,
    selection_justification: financeForm.value.selection_justification || undefined,
    committee_members: financeForm.value.committee_members || undefined,
  })
  if (result) {
    createdPors.value = (result as any).created_pors ?? []
    showFinanceModal.value = false
    await load()
  } else {
    financeError.value = store.veError
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

// ─── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  await store.fetchVe(props.id)
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors"
              @click="router.push('/planning/vendor-evaluations')">
        Đánh giá NCC
      </button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-mono font-semibold text-slate-700">{{ id }}</span>
      <StatusBadge v-if="doc" :state="doc.status" size="xs" class="ml-1" />
    </nav>

    <!-- Loading -->
    <SkeletonLoader v-if="store.veLoading" variant="form" />

    <!-- Error (no doc) -->
    <div v-else-if="store.veError && !doc" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.veError }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="load">Thử lại</button>
    </div>

    <template v-else-if="doc">

      <!-- Page header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03 · Đánh giá NCC</p>
          <h1 class="text-2xl font-bold text-slate-900 font-mono">{{ doc.name }}</h1>
          <div class="flex items-center gap-3 mt-2">
            <StatusBadge :state="doc.status" size="md" />
            <span class="text-sm text-slate-500">
              {{ formatDate(doc.evaluation_date) }}
            </span>
          </div>
        </div>

        <!-- Action buttons -->
        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
          <button
            v-if="store.canApproveTech"
            class="btn-primary"
            :disabled="store.veLoading"
            @click="showTechModal = true; actionError = null"
          >
            Duyệt kỹ thuật
          </button>
          <button
            v-if="store.canApproveFinance"
            class="btn-primary"
            :disabled="store.veLoading"
            @click="openFinanceModal"
          >
            Duyệt tài chính & Chốt NCC
          </button>
          <button class="btn-ghost" @click="router.back()">Quay lại</button>
        </div>
      </div>

      <!-- POR tự động tạo sau khi duyệt tài chính -->
      <div v-if="createdPors.length > 0" class="mb-5 p-4 rounded-xl bg-green-50 border border-green-200">
        <p class="text-sm font-semibold text-green-800 mb-2">
          ✓ Đã tự động tạo {{ createdPors.length }} Phiếu Yêu cầu Mua sắm (POR)
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="por in createdPors"
            :key="por"
            class="text-xs font-mono px-2 py-1 rounded bg-green-100 text-green-700 hover:bg-green-200 transition-colors"
            @click="router.push(`/planning/purchase-order-requests/${por}`)"
          >
            {{ por }} →
          </button>
        </div>
      </div>

      <!-- Action error inline -->
      <div v-if="actionError" class="alert-error mb-5">
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="flex-1">{{ actionError }}</span>
        <button class="text-xs font-medium" @click="actionError = null">✕</button>
      </div>

      <!-- Info + scoring grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">

        <!-- Left: Info card -->
        <div class="lg:col-span-1 space-y-5">

          <div class="card">
            <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
              Thông tin phiếu
            </h3>
            <dl class="space-y-3">
              <div>
                <dt class="text-xs text-slate-400">Kế hoạch mua sắm</dt>
                <dd>
                  <button
                    class="text-sm font-mono text-brand-600 hover:underline"
                    @click="router.push(`/planning/procurement-plans/${doc.linked_plan}`)"
                  >
                    {{ doc.linked_plan }}
                  </button>
                </dd>
              </div>
              <div v-if="doc.linked_technical_spec">
                <dt class="text-xs text-slate-400">Đặc tả kỹ thuật</dt>
                <dd>
                  <button
                    class="text-sm font-mono text-brand-600 hover:underline"
                    @click="router.push(`/planning/technical-specs/${doc.linked_technical_spec}`)"
                  >
                    {{ doc.linked_technical_spec }}
                  </button>
                </dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400">Ngày đánh giá</dt>
                <dd class="text-sm text-slate-700">{{ formatDate(doc.evaluation_date) }}</dd>
              </div>
            </dl>
          </div>

          <!-- Review/Approval info -->
          <div v-if="doc.tech_reviewed_by || doc.approved_by" class="card">
            <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
              Phê duyệt
            </h3>
            <dl class="space-y-3">
              <div v-if="doc.tech_reviewed_by">
                <dt class="text-xs text-slate-400">Duyệt kỹ thuật</dt>
                <dd class="text-sm text-slate-700">{{ doc.tech_reviewed_by }}</dd>
                <dd class="text-xs text-slate-400">{{ formatDate(doc.tech_review_date) }}</dd>
              </div>
              <div v-if="doc.approved_by">
                <dt class="text-xs text-slate-400">Duyệt tài chính</dt>
                <dd class="text-sm text-slate-700">{{ doc.approved_by }}</dd>
                <dd class="text-xs text-slate-400">{{ formatDate(doc.approval_date) }}</dd>
              </div>
            </dl>
          </div>

        </div>

        <!-- Right: Scoring table -->
        <div class="lg:col-span-2">
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
              Bảng chấm điểm nhà cung cấp ({{ doc.items.length }} NCC)
            </h3>
            <VendorScoringTable
              :items="doc.items"
              :editable="false"
              :recommended_vendor="doc.recommended_vendor ?? undefined"
            />
          </div>
        </div>

      </div>

      <!-- Result section (Approved) -->
      <div v-if="doc.status === 'Approved' && doc.recommended_vendor" class="card mb-6 bg-emerald-50 border border-emerald-100 animate-slide-up">
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
            <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div class="flex-1">
            <p class="text-sm font-semibold text-emerald-800 mb-1">
              NCC được chọn: <span class="font-mono">{{ doc.recommended_vendor }}</span>
            </p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
              <div v-if="doc.selection_justification">
                <p class="text-xs text-emerald-600 font-medium mb-1">Lý do lựa chọn</p>
                <p class="text-sm text-emerald-800 leading-relaxed">{{ doc.selection_justification }}</p>
              </div>
              <div v-if="doc.committee_members">
                <p class="text-xs text-emerald-600 font-medium mb-1">Thành viên hội đồng</p>
                <p class="text-sm text-emerald-800">{{ doc.committee_members }}</p>
              </div>
            </div>
            <div v-if="doc.approved_by" class="mt-3 text-xs text-emerald-600">
              Phê duyệt bởi {{ doc.approved_by }} — {{ formatDate(doc.approval_date) }}
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- ─── Tech Approval Modal ─── -->
    <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0"
                enter-to-class="opacity-100" leave-active-class="transition duration-100 ease-in"
                leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="showTechModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showTechModal = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-fade-in">
          <h3 class="text-base font-semibold text-slate-800 mb-1">Duyệt kỹ thuật</h3>
          <p class="text-sm text-slate-500 mb-5">Xác nhận kết quả đánh giá kỹ thuật của tất cả nhà cung cấp.</p>

          <div v-if="actionError" class="alert-error mb-4 text-sm">{{ actionError }}</div>

          <div class="form-group mb-4">
            <label class="form-label">Ghi chú kỹ thuật <span class="text-slate-400 text-xs">(tùy chọn)</span></label>
            <textarea v-model="techNotes" rows="3" class="form-input resize-none"
                      placeholder="Nhận xét, ghi chú kỹ thuật..." />
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showTechModal = false">Hủy</button>
            <button class="btn-primary" :disabled="store.veLoading" @click="handleApproveTech">
              <svg v-if="store.veLoading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Xác nhận duyệt kỹ thuật
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ─── Finance Approval Modal ─── -->
    <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0"
                enter-to-class="opacity-100" leave-active-class="transition duration-100 ease-in"
                leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="showFinanceModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showFinanceModal = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6 animate-fade-in">
          <h3 class="text-base font-semibold text-slate-800 mb-1">Duyệt tài chính & Chốt NCC</h3>
          <p class="text-sm text-slate-500 mb-5">Chọn nhà cung cấp được đề xuất và ghi lý do lựa chọn.</p>

          <div v-if="financeError" class="alert-error mb-4 text-sm">{{ financeError }}</div>

          <div class="space-y-4">
            <div class="form-group">
              <label class="form-label">NCC được đề xuất <span class="text-red-500">*</span></label>
              <select v-model="financeForm.recommended_vendor" class="form-select">
                <option value="">— Chọn nhà cung cấp —</option>
                <option
                  v-for="item in (doc?.items ?? [])"
                  :key="item.vendor"
                  :value="item.vendor"
                >
                  {{ item.vendor_name || item.vendor }}
                  ({{ item.total_score?.toFixed(2) }} điểm · {{ item.score_band }})
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Lý do lựa chọn <span class="text-red-500">*</span></label>
              <textarea v-model="financeForm.selection_justification" rows="3" class="form-input resize-none"
                        placeholder="Ghi rõ lý do chọn nhà cung cấp này..." />
            </div>
            <div class="form-group">
              <label class="form-label">Thành viên hội đồng <span class="text-slate-400 text-xs">(tùy chọn)</span></label>
              <input v-model="financeForm.committee_members" type="text" class="form-input"
                     placeholder="Ví dụ: Nguyễn Văn A, Trần Thị B..." />
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showFinanceModal = false">Hủy</button>
            <button class="btn-primary" :disabled="store.veLoading" @click="handleApproveFinance">
              <svg v-if="store.veLoading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Xác nhận duyệt tài chính
            </button>
          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>
