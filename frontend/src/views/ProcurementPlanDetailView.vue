<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ApprovalModal from '@/components/common/ApprovalModal.vue'
import { formatDate } from '@/utils/docUtils'
import type { ApprovedNA } from '@/api/imm02'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store  = useImm02Store()

const showAddPanel     = ref(false)
const showApproveModal = ref(false)
const showSubmitModal  = ref(false)
const approveNotes     = ref('')

const addForm = ref({
  needs_assessment: '',
  planned_quarter: '',
  estimated_unit_cost: null as number | null,
})
const addErrors  = ref<Record<string, string>>({})
const addLoading = ref(false)
const selectedNaInfo = ref<ApprovedNA | null>(null)
const naLoading = ref(false)

const doc = computed(() => store.currentDoc)

const budgetPct = computed(() => {
  if (!doc.value?.approved_budget) return 0
  return Math.min(100, Math.round((doc.value.allocated_budget / doc.value.approved_budget) * 100))
})

// Fetch approved NAs khi mở panel, lọc theo năm của kế hoạch hiện tại
watch(showAddPanel, async (open) => {
  if (open && doc.value && store.approvedNas.length === 0) {
    naLoading.value = true
    await store.fetchApprovedNas(doc.value.plan_year)
    naLoading.value = false
  }
})

function onNaSelect(naName: string) {
  addForm.value.needs_assessment = naName
  selectedNaInfo.value = store.approvedNas.find(n => n.name === naName) ?? null
  delete addErrors.value.needs_assessment
}

function formatBudget(val: number | null | undefined): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}

const PRIORITY_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  Critical: { bg: '#fef2f2', text: '#dc2626', label: 'Khẩn cấp' },
  High:     { bg: '#fff7ed', text: '#ea580c', label: 'Cao' },
  Medium:   { bg: '#fefce8', text: '#ca8a04', label: 'Trung bình' },
  Low:      { bg: '#f0fdf4', text: '#16a34a', label: 'Thấp' },
}

const ITEM_STATUS: Record<string, { label: string; color: string }> = {
  'Pending':      { label: 'Chờ xử lý',       color: '#94a3b8' },
  'Spec Defined': { label: 'Đã xác định ĐKT', color: '#0891b2' },
  'PO Raised':    { label: 'Đã tạo PO',        color: '#7c3aed' },
  'Ordered':      { label: 'Đã đặt hàng',      color: '#2563eb' },
  'Delivered':    { label: 'Đã giao hàng',     color: '#16a34a' },
  'Cancelled':    { label: 'Đã hủy',           color: '#94a3b8' },
}

function validateAdd(): boolean {
  const e: Record<string, string> = {}
  if (!addForm.value.needs_assessment) e.needs_assessment = 'Vui lòng chọn Phiếu nhu cầu mua sắm'
  addErrors.value = e
  return Object.keys(e).length === 0
}

async function submitAddItem() {
  if (!validateAdd()) return
  addLoading.value = true
  const ok = await store.addNa({
    plan_name: props.id,
    needs_assessment: addForm.value.needs_assessment,
    planned_quarter: addForm.value.planned_quarter || undefined,
    estimated_unit_cost: addForm.value.estimated_unit_cost ?? undefined,
  })
  addLoading.value = false
  if (ok) {
    showAddPanel.value = false
    addForm.value = { needs_assessment: '', planned_quarter: '', estimated_unit_cost: null }
    selectedNaInfo.value = null
    addErrors.value = {}
  }
}

async function handleSubmit(approver: string) {
  showSubmitModal.value = false
  await store.submitForReview(props.id, approver)
}

async function handleApprove() {
  const ok = await store.approvePlan(props.id, approveNotes.value || undefined)
  if (ok) { showApproveModal.value = false; approveNotes.value = '' }
}

async function handleLockBudget() { await store.lockBudget(props.id) }

function defineSpec(_itemName: string, _equipmentDesc: string, needsAssessment?: string) {
  const query = needsAssessment ? `?na=${needsAssessment}` : ''
  router.push(`/planning/technical-specs/new${query}`)
}

onMounted(() => store.fetchOne(props.id))
</script>

<template>
  <div class="page-container animate-fade-in">

    <SkeletonLoader v-if="store.loading" variant="form" />

    <div v-else-if="store.error && !doc" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ store.error }}</span>
    </div>

    <template v-else-if="doc">

      <!-- Header -->
      <div class="flex items-start justify-between mb-7">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-02</p>
          <h1 class="text-2xl font-bold text-slate-900 font-mono">{{ doc.name }}</h1>
          <div class="flex items-center gap-3 mt-2">
            <StatusBadge :state="doc.status" />
            <span class="text-sm text-slate-500">Năm: <strong class="text-slate-700">{{ doc.plan_year }}</strong></span>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap justify-end">
          <button v-if="store.canSubmitPlan" class="btn-primary"
                  :disabled="store.loading" @click="showSubmitModal = true">
            Gửi xét duyệt
          </button>
          <button v-if="store.canApprovePlan" class="btn-primary"
                  :disabled="store.loading" @click="showApproveModal = true">
            Duyệt kế hoạch
          </button>
          <button v-if="store.canLockBudget" class="btn-primary"
                  :disabled="store.loading" @click="handleLockBudget">
            Khóa ngân sách
          </button>
          <button class="btn-ghost" @click="router.back()">Quay lại</button>
        </div>
      </div>

      <div v-if="store.error" class="alert-error mb-4">
        <span class="flex-1">{{ store.error }}</span>
        <button class="text-xs font-semibold underline" @click="store.clearError">Đóng</button>
      </div>

      <!-- Budget summary -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div class="card animate-slide-up" style="animation-delay:0ms">
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Ngân sách duyệt</p>
          <p class="text-xl font-bold text-slate-900">{{ formatBudget(doc.approved_budget) }}</p>
        </div>
        <div class="card animate-slide-up" style="animation-delay:40ms">
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Đã phân bổ</p>
          <p class="text-xl font-bold text-slate-900">{{ formatBudget(doc.allocated_budget) }}</p>
          <div class="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500"
                 :style="{
                   width: `${budgetPct}%`,
                   background: budgetPct > 90 ? '#ef4444' : budgetPct > 70 ? '#f59e0b' : '#10b981',
                 }" />
          </div>
          <p class="text-xs text-slate-400 mt-1">{{ budgetPct }}% đã sử dụng</p>
        </div>
        <div class="card animate-slide-up" style="animation-delay:80ms">
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Còn lại</p>
          <p class="text-xl font-bold" :class="(doc.remaining_budget ?? 0) < 0 ? 'text-red-600' : 'text-slate-900'">
            {{ formatBudget(doc.remaining_budget) }}
          </p>
        </div>
      </div>

      <!-- Approval banner -->
      <div v-if="doc.approved_by" class="card mb-6 bg-emerald-50 border border-emerald-100 animate-slide-up">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
            <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-emerald-800">Đã duyệt bởi {{ doc.approved_by }}</p>
            <p class="text-xs text-emerald-600">{{ formatDate(doc.approval_date ?? '') }}</p>
            <p v-if="doc.approval_notes" class="text-xs text-emerald-700 mt-0.5">{{ doc.approval_notes }}</p>
          </div>
        </div>
      </div>

      <!-- Items -->
      <div class="card animate-slide-up" style="animation-delay:120ms">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-semibold text-slate-700">Nhu cầu mua sắm ({{ doc.items.length }})</h2>
          <button v-if="doc.status === 'Draft'" class="btn-primary text-xs"
                  @click="showAddPanel = !showAddPanel">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Thêm nhu cầu
          </button>
        </div>

        <!-- Add panel — chọn NA -->
        <Transition name="slide-fade">
          <div v-if="showAddPanel" class="mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">
              Gắn Phiếu nhu cầu mua sắm
            </h3>
            <div class="space-y-4">
              <div class="form-group">
                <label class="form-label">Phiếu nhu cầu mua sắm <span class="text-red-500">*</span></label>
                <div v-if="naLoading" class="text-xs text-slate-400 py-2">Đang tải danh sách...</div>
                <select
                  v-else
                  v-model="addForm.needs_assessment"
                  class="form-select"
                  :class="{ 'border-red-400': addErrors.needs_assessment }"
                  @change="onNaSelect(addForm.needs_assessment)"
                >
                  <option value="">— Chọn phiếu nhu cầu đã duyệt —</option>
                  <option
                    v-for="na in store.approvedNas"
                    :key="na.name"
                    :value="na.name"
                  >
                    {{ na.name }} · {{ na.equipment_type }} (SL: {{ na.quantity }}, Ưu tiên: {{ na.priority }})
                  </option>
                </select>
                <p v-if="addErrors.needs_assessment" class="mt-1 text-xs text-red-500">
                  {{ addErrors.needs_assessment }}
                </p>
                <p v-if="!naLoading && store.approvedNas.length === 0" class="mt-1 text-xs text-amber-600">
                  Không có phiếu nhu cầu nào đã duyệt trong năm {{ doc?.plan_year }}.
                </p>
              </div>

              <!-- Preview NA info — hiển thị sau khi chọn -->
              <div v-if="selectedNaInfo"
                   class="p-3 bg-blue-50 rounded-lg border border-blue-100 text-xs text-blue-900 grid grid-cols-2 gap-x-4 gap-y-1.5">
                <div>
                  <span class="text-blue-500 font-medium">Thiết bị:</span>
                  <span class="ml-1 font-semibold">{{ selectedNaInfo.equipment_type }}</span>
                </div>
                <div>
                  <span class="text-blue-500 font-medium">Số lượng:</span>
                  <span class="ml-1 font-semibold">{{ selectedNaInfo.quantity }}</span>
                </div>
                <div>
                  <span class="text-blue-500 font-medium">Ưu tiên:</span>
                  <span class="ml-1 font-semibold">{{ selectedNaInfo.priority }}</span>
                </div>
                <div>
                  <span class="text-blue-500 font-medium">Ngân sách duyệt:</span>
                  <span class="ml-1 font-semibold">{{ formatBudget(selectedNaInfo.approved_budget || selectedNaInfo.estimated_budget) }}</span>
                </div>
                <div>
                  <span class="text-blue-500 font-medium">Khoa/Phòng:</span>
                  <span class="ml-1">{{ selectedNaInfo.requesting_dept || '—' }}</span>
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="form-group">
                  <label class="form-label">Quý kế hoạch</label>
                  <select v-model="addForm.planned_quarter" class="form-select">
                    <option value="">— Chưa xác định —</option>
                    <option value="Q1">Q1</option>
                    <option value="Q2">Q2</option>
                    <option value="Q3">Q3</option>
                    <option value="Q4">Q4</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">
                    Đơn giá ước tính (VNĐ)
                    <span class="text-xs font-normal text-slate-400 ml-1">(để trống = tính từ ngân sách NA)</span>
                  </label>
                  <input v-model.number="addForm.estimated_unit_cost" type="number" min="0" class="form-input"
                         placeholder="Để trống = tính từ ngân sách được duyệt" />
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2 mt-4 pt-4 border-t border-slate-200">
              <button class="btn-primary" :disabled="addLoading || !addForm.needs_assessment" @click="submitAddItem">
                {{ addLoading ? 'Đang lưu…' : 'Thêm vào kế hoạch' }}
              </button>
              <button class="btn-ghost" @click="showAddPanel = false; addErrors = {}; addForm.needs_assessment = ''; selectedNaInfo = null">Hủy</button>
            </div>
          </div>
        </Transition>

        <div v-if="doc.items.length" class="table-wrapper -mx-0 overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-100">
            <thead>
              <tr>
                <th class="table-header">Phiếu nhu cầu</th>
                <th class="table-header">Thiết bị</th>
                <th class="table-header text-center">SL</th>
                <th class="table-header text-right">Tổng chi phí</th>
                <th class="table-header">Ưu tiên</th>
                <th class="table-header">Quý</th>
                <th class="table-header">Trạng thái</th>
                <th class="table-header">Thao tác</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-slate-100">
              <tr v-for="(item, i) in doc.items" :key="item.name"
                  class="hover:bg-slate-50 transition-colors"
                  :style="`animation-delay: ${i * 20}ms`">
                <td class="table-cell">
                  <span class="text-xs font-mono text-brand-600 font-semibold">
                    {{ item.needs_assessment || '—' }}
                  </span>
                </td>
                <td class="table-cell">
                  <p class="font-medium text-slate-800 text-sm">{{ item.equipment_description }}</p>
                </td>
                <td class="table-cell text-center text-slate-700">{{ item.quantity }}</td>
                <td class="table-cell text-right font-semibold text-slate-800">{{ formatBudget(item.total_cost) }}</td>
                <td class="table-cell">
                  <span v-if="PRIORITY_CONFIG[item.priority]"
                        class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
                        :style="{ background: PRIORITY_CONFIG[item.priority].bg, color: PRIORITY_CONFIG[item.priority].text }">
                    {{ PRIORITY_CONFIG[item.priority].label }}
                  </span>
                </td>
                <td class="table-cell text-slate-500 text-sm">{{ item.planned_quarter || '—' }}</td>
                <td class="table-cell">
                  <span class="inline-flex items-center gap-1.5 text-xs font-semibold"
                        :style="{ color: ITEM_STATUS[item.status]?.color ?? '#94a3b8' }">
                    <span class="w-1.5 h-1.5 rounded-full shrink-0"
                          :style="{ background: ITEM_STATUS[item.status]?.color ?? '#94a3b8' }" />
                    {{ ITEM_STATUS[item.status]?.label ?? item.status }}
                  </span>
                </td>
                <td class="table-cell">
                  <button v-if="item.status === 'Pending' && doc.status === 'Approved'"
                          class="btn-primary text-xs py-1.5 px-3 whitespace-nowrap"
                          @click="defineSpec(item.name, item.equipment_description, item.needs_assessment ?? undefined)">
                    Xác định ĐKT
                  </button>
                  <span v-else class="text-xs text-slate-400">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="py-12 text-center">
          <div class="flex flex-col items-center gap-3 text-slate-400">
            <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p class="text-sm">Chưa có nhu cầu mua sắm nào trong kế hoạch.</p>
            <button v-if="doc.status === 'Draft'" class="btn-primary text-xs" @click="showAddPanel = true">
              Thêm ngay
            </button>
          </div>
        </div>
      </div>

    </template>

    <!-- Approve Modal -->
    <Transition name="fade">
      <div v-if="showApproveModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 animate-slide-up">
          <h3 class="text-base font-semibold text-slate-900 mb-4">Duyệt kế hoạch mua sắm</h3>
          <div class="form-group mb-4">
            <label class="form-label">Ghi chú duyệt (tùy chọn)</label>
            <textarea v-model="approveNotes" class="form-textarea" rows="3" placeholder="Nhập ghi chú…" />
          </div>
          <div class="flex items-center gap-2 pt-2">
            <button class="btn-primary flex-1" :disabled="store.loading" @click="handleApprove">
              {{ store.loading ? 'Đang xử lý…' : 'Xác nhận duyệt' }}
            </button>
            <button class="btn-ghost" @click="showApproveModal = false">Hủy</button>
          </div>
        </div>
      </div>
    </Transition>

  </div>

  <ApprovalModal
    :show="showSubmitModal"
    title="Gửi xét duyệt — Chọn người phê duyệt"
    :loading="store.loading"
    @confirm="handleSubmit"
    @cancel="showSubmitModal = false"
  />
</template>

<style scoped>
.slide-fade-enter-active, .slide-fade-leave-active { transition: all .2s ease; }
.slide-fade-enter-from, .slide-fade-leave-to { opacity: 0; transform: translateY(-8px); }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
