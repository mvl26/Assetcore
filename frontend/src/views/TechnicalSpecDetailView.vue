<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm02Store } from '@/stores/imm02'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ApprovalModal from '@/components/common/ApprovalModal.vue'
import { formatDate } from '@/utils/docUtils'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store  = useImm02Store()

const showApproveModal = ref(false)
const showSubmitModal  = ref(false)
const reviewNotes      = ref('')

const doc = computed(() => store.currentTs)

async function handleSubmit(approver: string) {
  showSubmitModal.value = false
  await store.submitTs(props.id, approver)
}

async function handleApprove() {
  const ok = await store.approveTs(props.id, reviewNotes.value || undefined)
  if (ok) { showApproveModal.value = false; reviewNotes.value = '' }
}

const REGULATORY_LABELS: Record<string, string> = {
  'Class I':   'Class I — Rủi ro thấp',
  'Class IIa': 'Class IIa — Rủi ro trung bình thấp',
  'Class IIb': 'Class IIb — Rủi ro trung bình cao',
  'Class III': 'Class III — Rủi ro cao',
}

onMounted(() => store.fetchTs(props.id))
</script>

<template>
  <div class="page-container animate-fade-in">

    <SkeletonLoader v-if="store.tsLoading" variant="form" />

    <div v-else-if="store.tsError && !doc" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ store.tsError }}</span>
    </div>

    <template v-else-if="doc">

      <!-- Header -->
      <div class="flex items-start justify-between mb-7">
        <div>
          <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-03</p>
          <h1 class="text-2xl font-bold text-slate-900 font-mono">{{ doc.name }}</h1>
          <div class="flex items-center gap-3 mt-2">
            <StatusBadge :state="doc.status" />
            <span class="text-sm text-slate-500 font-mono text-xs">{{ doc.regulatory_class }}</span>
          </div>
          <p class="text-sm text-slate-600 mt-1">{{ doc.equipment_description }}</p>
        </div>
        <div class="flex items-center gap-2 flex-wrap justify-end">
          <button v-if="store.canSubmitTs" class="btn-primary"
                  :disabled="store.tsLoading" @click="showSubmitModal = true">
            Gửi xét duyệt
          </button>
          <button v-if="store.canApproveTs" class="btn-primary"
                  :disabled="store.tsLoading" @click="showApproveModal = true">
            Duyệt đặc tả
          </button>
          <button class="btn-ghost" @click="router.back()">Quay lại</button>
        </div>
      </div>

      <div v-if="store.tsError" class="alert-error mb-4">
        <span class="flex-1">{{ store.tsError }}</span>
        <button class="text-xs font-semibold underline" @click="store.clearError">Đóng</button>
      </div>

      <!-- Review info -->
      <div v-if="doc.reviewed_by" class="card mb-6 bg-emerald-50 border border-emerald-100 animate-slide-up">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
            <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-emerald-800">Đã duyệt bởi {{ doc.reviewed_by }}</p>
            <p class="text-xs text-emerald-600">{{ formatDate(doc.review_date ?? '') }}</p>
            <p v-if="doc.review_notes" class="text-xs text-emerald-700 mt-0.5">{{ doc.review_notes }}</p>
          </div>
        </div>
      </div>

      <!-- Linked NA -->
      <div v-if="doc.needs_assessment" class="card mb-6 animate-slide-up" style="animation-delay:0ms">
        <p class="text-xs text-slate-400 mb-0.5">Phiếu nhu cầu mua sắm</p>
        <router-link :to="`/planning/needs-assessments/${doc.needs_assessment}`"
                     class="font-mono text-xs font-semibold text-brand-600 hover:underline">
          {{ doc.needs_assessment }}
        </router-link>
      </div>

      <!-- Technical info -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">

        <!-- Classification -->
        <div class="card animate-slide-up" style="animation-delay:40ms">
          <h2 class="text-sm font-semibold text-slate-700 mb-3">Phân loại</h2>
          <dl class="space-y-2 text-sm">
            <div>
              <dt class="text-xs text-slate-400">Phân loại thiết bị y tế</dt>
              <dd class="font-semibold text-slate-800">
                {{ REGULATORY_LABELS[doc.regulatory_class] ?? doc.regulatory_class }}
              </dd>
            </div>
            <div v-if="doc.mdd_class">
              <dt class="text-xs text-slate-400">Phân loại MDD</dt>
              <dd class="text-slate-700">{{ doc.mdd_class }}</dd>
            </div>
            <div v-if="doc.device_model">
              <dt class="text-xs text-slate-400">Mẫu thiết bị</dt>
              <dd class="text-slate-700">{{ doc.device_model }}</dd>
            </div>
            <div v-if="doc.reference_standard">
              <dt class="text-xs text-slate-400">Tiêu chuẩn tham chiếu</dt>
              <dd class="text-slate-700">{{ doc.reference_standard }}</dd>
            </div>
          </dl>
        </div>

        <!-- Delivery & Warranty -->
        <div class="card animate-slide-up" style="animation-delay:60ms">
          <h2 class="text-sm font-semibold text-slate-700 mb-3">Bàn giao & Bảo hành</h2>
          <dl class="space-y-2 text-sm">
            <div v-if="doc.warranty_terms">
              <dt class="text-xs text-slate-400">Điều khoản bảo hành</dt>
              <dd class="text-slate-700">{{ doc.warranty_terms }}</dd>
            </div>
            <div v-if="doc.expected_delivery_weeks">
              <dt class="text-xs text-slate-400">Thời gian giao hàng</dt>
              <dd class="text-slate-700">{{ doc.expected_delivery_weeks }} tuần</dd>
            </div>
            <div v-if="!doc.warranty_terms && !doc.expected_delivery_weeks">
              <p class="text-xs text-slate-400 italic">Chưa có thông tin bàn giao.</p>
            </div>
          </dl>
        </div>
      </div>

      <!-- Requirements -->
      <div class="card mb-6 animate-slide-up" style="animation-delay:80ms">
        <h2 class="text-sm font-semibold text-slate-700 mb-4">Yêu cầu kỹ thuật</h2>
        <div class="grid grid-cols-1 gap-5">
          <div>
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Yêu cầu hiệu năng</p>
            <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{{ doc.performance_requirements }}</p>
          </div>
          <div class="border-t border-slate-100 pt-4">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Tiêu chuẩn an toàn</p>
            <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{{ doc.safety_standards }}</p>
          </div>
          <div v-if="doc.accessories_included" class="border-t border-slate-100 pt-4">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Phụ kiện đi kèm</p>
            <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{{ doc.accessories_included }}</p>
          </div>
          <div v-if="doc.installation_requirements" class="border-t border-slate-100 pt-4">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Yêu cầu lắp đặt</p>
            <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{{ doc.installation_requirements }}</p>
          </div>
          <div v-if="doc.training_requirements" class="border-t border-slate-100 pt-4">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Yêu cầu đào tạo</p>
            <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{{ doc.training_requirements }}</p>
          </div>
        </div>
      </div>

    </template>

    <!-- Approve Modal -->
    <Transition name="fade">
      <div v-if="showApproveModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 animate-slide-up">
          <h3 class="text-base font-semibold text-slate-900 mb-4">Duyệt đặc tả kỹ thuật</h3>
          <div class="form-group mb-4">
            <label class="form-label">Ghi chú xét duyệt (tùy chọn)</label>
            <textarea v-model="reviewNotes" class="form-textarea" rows="3"
                      placeholder="Nhập ghi chú xét duyệt…" />
          </div>
          <div class="flex items-center gap-2 pt-2">
            <button class="btn-primary flex-1" :disabled="store.tsLoading" @click="handleApprove">
              {{ store.tsLoading ? 'Đang xử lý…' : 'Xác nhận duyệt' }}
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
    :loading="store.tsLoading"
    @confirm="handleSubmit"
    @cancel="showSubmitModal = false"
  />
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
