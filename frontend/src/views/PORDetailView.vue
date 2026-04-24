<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useImm03Store } from '@/stores/imm03'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ApprovalModal from '@/components/common/ApprovalModal.vue'
import { formatDate } from '@/utils/docUtils'
import { getPpItemsForPlan } from '@/api/imm03'
import type { PpItem } from '@/api/imm03'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store  = useImm03Store()

const doc = computed(() => store.currentPor)

// ─── PP Items (phân trang) ────────────────────────────────────────────────────
const ppItems      = ref<PpItem[]>([])
const ppTotal      = ref(0)
const ppPage       = ref(1)
const ppLoading    = ref(false)
const PP_PAGE_SIZE = 10

const ppTotalPages = computed(() => Math.ceil(ppTotal.value / PP_PAGE_SIZE))

async function loadPpItems(page = 1) {
  const planName = store.currentPor?.procurement_plan
  if (!planName) return
  ppLoading.value = true
  try {
    const res = await getPpItemsForPlan(planName, page, PP_PAGE_SIZE)
    ppItems.value = res.items
    ppTotal.value = res.total
    ppPage.value  = res.page
  } catch { /* silent */ }
  finally { ppLoading.value = false }
}

function ppStatusColor(status: string | undefined): string {
  switch (status) {
    case 'Pending':   return 'text-slate-500 bg-slate-100'
    case 'PO Raised': return 'text-blue-700 bg-blue-50'
    case 'Ordered':   return 'text-amber-700 bg-amber-50'
    case 'Delivered': return 'text-emerald-700 bg-emerald-50'
    default:          return 'text-slate-400 bg-slate-50'
  }
}

function ppStatusLabel(status: string | undefined): string {
  switch (status) {
    case 'Pending':   return 'Chờ mua'
    case 'PO Raised': return 'Đã tạo POR'
    case 'Ordered':   return 'Đã đặt hàng'
    case 'Delivered': return 'Đã giao'
    default:          return status ?? '—'
  }
}

// ─── Modals ───────────────────────────────────────────────────────────────────
const showSubmitModal    = ref(false)
const showDeliveryModal  = ref(false)
const deliveryNotes      = ref('')
const actionError        = ref<string | null>(null)

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatBudget(val: number | null | undefined): string {
  if (!val) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(val)
}

// ─── Actions ──────────────────────────────────────────────────────────────────

async function handleSubmit(approver: string) {
  showSubmitModal.value = false
  actionError.value = null
  const ok = await store.submitPor(props.id, approver)
  if (!ok) actionError.value = store.error
}

async function handleApprove() {
  if (!confirm('Xác nhận phê duyệt phiếu mua sắm này?')) return
  actionError.value = null
  const ok = await store.doApprovePor(props.id)
  if (!ok) actionError.value = store.error
}

async function handleRelease() {
  if (!confirm('Xác nhận phát hành POR? Thao tác này sẽ gửi phiếu đặt hàng đến nhà cung cấp.')) return
  actionError.value = null
  const ok = await store.doReleasePor(props.id)
  if (!ok) actionError.value = store.error
}

async function handleFulfill() {
  actionError.value = null
  const ok = await store.doFulfillPor(props.id, deliveryNotes.value || undefined)
  if (ok) {
    showDeliveryModal.value = false
    deliveryNotes.value = ''
  } else {
    actionError.value = store.error
  }
}

// ─── Load ─────────────────────────────────────────────────────────────────────
async function load() {
  await store.fetchPor(props.id)
  ppPage.value = 1
  await loadPpItems(1)
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors"
              @click="router.push('/planning/purchase-order-requests')">
        Yêu cầu Mua sắm
      </button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-mono font-semibold text-slate-700">{{ id }}</span>
      <StatusBadge v-if="doc" :state="doc.status" size="xs" class="ml-1" />
    </nav>

    <!-- Loading -->
    <SkeletonLoader v-if="store.loading" variant="form" />

    <!-- Error (no doc) -->
    <div v-else-if="store.error && !doc" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline hover:no-underline" @click="load">Thử lại</button>
    </div>

    <template v-else-if="doc">

      <!-- Page header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03 · Yêu cầu Mua sắm</p>
          <h1 class="text-2xl font-bold text-slate-900 font-mono">{{ doc.name }}</h1>
          <div class="flex items-center gap-2 mt-2 flex-wrap">
            <StatusBadge :state="doc.status" size="md" />
            <span v-if="doc.requires_director_approval"
                  class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">
              ⚠ Cần phê duyệt Giám đốc
            </span>
          </div>
        </div>

        <!-- Action buttons -->
        <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
          <button
            v-if="store.canSubmitPor"
            class="btn-primary"
            :disabled="store.loading"
            @click="showSubmitModal = true; actionError = null"
          >
            Gửi phê duyệt
          </button>
          <button
            v-if="store.canApprovePor"
            class="btn-primary"
            :disabled="store.loading"
            @click="handleApprove"
          >
            Phê duyệt
          </button>
          <button
            v-if="store.canReleasePor"
            class="btn-primary"
            :disabled="store.loading"
            @click="handleRelease"
          >
            Phát hành POR
          </button>
          <button
            v-if="store.canFulfillPor"
            class="btn-primary"
            :disabled="store.loading"
            @click="showDeliveryModal = true; actionError = null"
          >
            Xác nhận giao hàng
          </button>
          <button class="btn-ghost" @click="router.back()">Quay lại</button>
        </div>
      </div>

      <!-- Action error -->
      <div v-if="actionError" class="alert-error mb-5">
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="flex-1">{{ actionError }}</span>
        <button class="text-xs font-medium" @click="actionError = null">✕</button>
      </div>

      <!-- Store error (inline) -->
      <div v-if="store.error" class="alert-error mb-5">
        <span class="flex-1">{{ store.error }}</span>
        <button class="text-xs font-medium" @click="store.error = null">✕</button>
      </div>

      <!-- Main info grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

        <!-- Left: Thông tin thiết bị -->
        <div class="card animate-slide-up" style="animation-delay:0ms">
          <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
            Thông tin thiết bị
          </h3>
          <dl class="space-y-3">
            <div>
              <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Thiết bị</dt>
              <dd class="text-sm font-medium text-slate-800">{{ doc.equipment_description }}</dd>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Số lượng</dt>
                <dd class="text-sm text-slate-700 font-semibold">{{ doc.quantity }}</dd>
              </div>
              <div>
                <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Đơn giá</dt>
                <dd class="text-sm text-slate-700 font-semibold">{{ formatBudget(doc.unit_price) }}</dd>
              </div>
            </div>
            <div>
              <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Tổng giá trị</dt>
              <dd class="text-xl font-bold text-slate-900">{{ formatBudget(doc.total_amount) }}</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Nhà cung cấp</dt>
              <dd class="text-sm font-semibold text-slate-800">
                {{ doc.vendor_name || doc.vendor }}
                <span v-if="doc.vendor_name" class="font-normal text-slate-500 font-mono text-xs ml-1">({{ doc.vendor }})</span>
              </dd>
            </div>
          </dl>
        </div>

        <!-- Right: Liên kết -->
        <div class="card animate-slide-up" style="animation-delay:40ms">
          <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
            Liên kết
          </h3>
          <dl class="space-y-3">
            <div v-if="doc.linked_evaluation">
              <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Phiếu đánh giá NCC</dt>
              <dd>
                <button
                  class="text-sm font-mono text-brand-600 hover:underline"
                  @click="router.push(`/planning/vendor-evaluations/${doc.linked_evaluation}`)"
                >
                  {{ doc.linked_evaluation }} →
                </button>
              </dd>
            </div>
            <div v-if="doc.linked_technical_spec">
              <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Đặc tả kỹ thuật</dt>
              <dd>
                <button
                  class="text-sm font-mono text-brand-600 hover:underline"
                  @click="router.push(`/planning/technical-specs/${doc.linked_technical_spec}`)"
                >
                  {{ doc.linked_technical_spec }} →
                </button>
              </dd>
            </div>
            <div v-if="doc.procurement_plan">
              <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Kế hoạch mua sắm</dt>
              <dd>
                <button
                  class="text-sm font-mono text-brand-600 hover:underline"
                  @click="router.push(`/planning/procurement-plans/${doc.procurement_plan}`)"
                >
                  {{ doc.procurement_plan }} →
                </button>
              </dd>
            </div>
            <div v-if="doc.linked_plan_item">
              <dt class="text-xs text-slate-400 uppercase tracking-wide mb-0.5">Hạng mục KHMS</dt>
              <dd class="text-sm font-mono text-slate-700">{{ doc.linked_plan_item }}</dd>
            </div>
          </dl>
        </div>

      </div>

      <!-- Terms card -->
      <div class="card mb-6 animate-slide-up" style="animation-delay:80ms">
        <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
          Điều khoản hợp đồng
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Điều khoản giao hàng</p>
            <p class="text-sm text-slate-700">{{ doc.delivery_terms || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Điều khoản thanh toán</p>
            <p class="text-sm text-slate-700">{{ doc.payment_terms || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Ngày giao hàng dự kiến</p>
            <p class="text-sm text-slate-700">{{ doc.expected_delivery_date ? formatDate(doc.expected_delivery_date) : '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Bảo hành</p>
            <p class="text-sm text-slate-700">
              {{ doc.warranty_period_months ? `${doc.warranty_period_months} tháng` : '—' }}
            </p>
          </div>
          <div v-if="doc.waiver_reason" class="sm:col-span-2">
            <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Lý do miễn trừ (VR-03-07)</p>
            <p class="text-sm text-amber-800 bg-amber-50 px-3 py-2 rounded-lg border border-amber-100">
              {{ doc.waiver_reason }}
            </p>
          </div>
        </div>
      </div>

      <!-- PP Items table -->
      <div v-if="doc.procurement_plan" class="card mb-6 animate-slide-up" style="animation-delay:120ms">
        <div class="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
          <div>
            <h3 class="text-sm font-semibold text-slate-700">
              Hạng mục Kế hoạch mua sắm
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">
              {{ doc.procurement_plan }} · {{ ppTotal }} hạng mục
            </p>
          </div>
          <button
            class="text-xs font-mono text-brand-600 hover:underline"
            @click="router.push(`/planning/procurement-plans/${doc.procurement_plan}`)"
          >
            Xem kế hoạch →
          </button>
        </div>

        <!-- Loading skeleton -->
        <div v-if="ppLoading" class="space-y-2">
          <div v-for="n in 5" :key="n" class="h-10 bg-slate-100 rounded animate-pulse" />
        </div>

        <!-- Table -->
        <template v-else>
          <div class="overflow-x-auto -mx-5">
            <table class="min-w-full">
              <thead>
                <tr class="border-b border-slate-100">
                  <th class="px-5 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide w-10">#</th>
                  <th class="px-5 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Tên thiết bị</th>
                  <th class="px-5 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wide w-20">SL</th>
                  <th class="px-5 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase tracking-wide w-36">Ngân sách</th>
                  <th class="px-5 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase tracking-wide w-32">Trạng thái</th>
                  <th class="px-5 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide w-36">POR</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr
                  v-for="(item, i) in ppItems"
                  :key="item.name"
                  class="hover:bg-slate-50 transition-colors"
                  :class="{ 'bg-brand-50/40': item.name === doc.linked_plan_item }"
                >
                  <td class="px-5 py-3 text-xs text-slate-400 font-mono">
                    {{ (ppPage - 1) * PP_PAGE_SIZE + i + 1 }}
                  </td>
                  <td class="px-5 py-3">
                    <span class="text-sm text-slate-800">{{ item.equipment_description }}</span>
                    <span v-if="item.name === doc.linked_plan_item"
                          class="ml-2 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-brand-100 text-brand-700">
                      Hạng mục này
                    </span>
                  </td>
                  <td class="px-5 py-3 text-right text-sm text-slate-700 font-semibold">
                    {{ item.quantity }}
                  </td>
                  <td class="px-5 py-3 text-right text-sm text-slate-600 font-mono">
                    {{ item.total_cost ? formatBudget(item.total_cost) : '—' }}
                  </td>
                  <td class="px-5 py-3 text-center">
                    <span class="inline-block px-2 py-0.5 rounded-full text-xs font-semibold"
                          :class="ppStatusColor(item.status)">
                      {{ ppStatusLabel(item.status) }}
                    </span>
                  </td>
                  <td class="px-5 py-3">
                    <button
                      v-if="item.por_reference"
                      class="text-xs font-mono text-brand-600 hover:underline"
                      @click="router.push(`/planning/purchase-order-requests/${item.por_reference}`)"
                    >
                      {{ item.por_reference }}
                    </button>
                    <span v-else class="text-xs text-slate-300">—</span>
                  </td>
                </tr>
                <tr v-if="ppItems.length === 0">
                  <td colspan="6" class="px-5 py-8 text-center text-sm text-slate-400">
                    Không có hạng mục nào.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div v-if="ppTotalPages > 1" class="flex items-center justify-between pt-4 mt-2 border-t border-slate-100">
            <p class="text-xs text-slate-400">
              Trang {{ ppPage }}/{{ ppTotalPages }} · {{ ppTotal }} hạng mục
            </p>
            <div class="flex items-center gap-1">
              <button
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 text-slate-600
                       hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                :disabled="ppPage <= 1"
                @click="loadPpItems(ppPage - 1)"
              >
                ‹ Trước
              </button>
              <button
                v-for="p in ppTotalPages"
                :key="p"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                :class="p === ppPage
                  ? 'bg-brand-600 text-white border border-brand-600'
                  : 'border border-slate-200 text-slate-600 hover:bg-slate-50'"
                @click="loadPpItems(p)"
              >
                {{ p }}
              </button>
              <button
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 text-slate-600
                       hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                :disabled="ppPage >= ppTotalPages"
                @click="loadPpItems(ppPage + 1)"
              >
                Sau ›
              </button>
            </div>
          </div>
        </template>
      </div>

      <!-- Approval card (if approved / released / fulfilled) -->
      <div v-if="doc.approved_by || doc.released_by"
           class="card mb-6 animate-slide-up" style="animation-delay:120ms">
        <h3 class="text-sm font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
          Phê duyệt & Phát hành
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-if="doc.approved_by">
            <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Phê duyệt bởi</p>
            <p class="text-sm font-semibold text-slate-800">{{ doc.approved_by }}</p>
            <p class="text-xs text-slate-400">{{ formatDate(doc.approval_date) }}</p>
          </div>
          <div v-if="doc.released_by">
            <p class="text-xs text-slate-400 uppercase tracking-wide mb-1">Phát hành bởi</p>
            <p class="text-sm font-semibold text-slate-800">{{ doc.released_by }}</p>
            <p class="text-xs text-slate-400">{{ formatDate(doc.release_date) }}</p>
          </div>
        </div>
      </div>

    </template>

    <!-- Submit modal -->
    <ApprovalModal
      :show="showSubmitModal"
      title="Gửi phê duyệt — Chọn người phê duyệt"
      :loading="store.loading"
      @confirm="handleSubmit"
      @cancel="showSubmitModal = false"
    />

    <!-- Delivery confirmation modal -->
    <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0"
                enter-to-class="opacity-100" leave-active-class="transition duration-100 ease-in"
                leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="showDeliveryModal"
           class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
           @click.self="showDeliveryModal = false">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-fade-in">
          <h3 class="text-base font-semibold text-slate-800 mb-1">Xác nhận giao hàng</h3>
          <p class="text-sm text-slate-500 mb-5">Xác nhận đã nhận được hàng từ nhà cung cấp.</p>

          <div v-if="actionError" class="alert-error mb-4 text-sm">{{ actionError }}</div>

          <div class="form-group mb-4">
            <label class="form-label">Ghi chú giao hàng <span class="text-slate-400 text-xs">(tùy chọn)</span></label>
            <textarea v-model="deliveryNotes" rows="3" class="form-input resize-none"
                      placeholder="Tình trạng hàng hóa, số lô, ngày nhận thực tế..." />
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button class="btn-ghost" @click="showDeliveryModal = false">Hủy</button>
            <button class="btn-primary" :disabled="store.loading" @click="handleFulfill">
              <svg v-if="store.loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Xác nhận nhận hàng
            </button>
          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>
