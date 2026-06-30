<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Chi tiết Phát hiện: confirm / mark FP / waive / link CAPA / create CAPA.
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { getFinding } from '@/api/imm16'
import type { ComplianceFinding } from '@/api/imm16'
import { formatDate, formatAssetDisplay } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import RecordHistory from '@/components/common/RecordHistory.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store = useImm16Store()
const api = useApi()

const finding = ref<ComplianceFinding | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    finding.value = await getFinding(props.id)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const canConfirm = computed(() =>
  finding.value && ['Open', 'Under Review'].includes(finding.value.status))
const canWaive = computed(() =>
  finding.value && !['Waived', 'Closed', 'False Positive'].includes(finding.value.status))
const canCreateCapa = computed(() =>
  finding.value && finding.value.status === 'Confirmed NC' && !finding.value.capa_ref)

// ── Confirm ──
const reviewerNote = ref('')
const showConfirm = ref(false)
async function doConfirm() {
  if (!finding.value) return
  const res = await api.run(() => store.actionConfirmFinding(finding.value!.name, reviewerNote.value), {
    successMessage: 'Đã xác nhận phát hiện',
  })
  if (res) { showConfirm.value = false; reviewerNote.value = ''; await load() }
}

// ── Mark False Positive ──
const showFP = ref(false)
const fpReason = ref('')
async function doFP() {
  if (!finding.value) return
  if (fpReason.value.trim().length < 10) {
    alert('Lý do tối thiểu 10 ký tự')
    return
  }
  const res = await api.run(() => store.actionMarkFalsePositive(finding.value!.name, fpReason.value), {
    successMessage: 'Đã đánh dấu sai',
  })
  if (res) { showFP.value = false; fpReason.value = ''; await load() }
}

// ── Waive ──
const showWaive = ref(false)
const waiveReason = ref('')
const waiveEvidence = ref('')
const waiveExpiry = ref('')
async function doWaive() {
  if (!finding.value) return
  if (waiveReason.value.trim().length < 50) {
    alert('Lý do miễn tối thiểu 50 ký tự (VR-04)')
    return
  }
  if (!waiveEvidence.value || !waiveExpiry.value) {
    alert('Thiếu bằng chứng hoặc ngày hết hiệu lực')
    return
  }
  const res = await api.run(
    () => store.actionWaiveFinding(finding.value!.name, waiveReason.value, waiveEvidence.value, waiveExpiry.value),
    { successMessage: 'Đã miễn áp dụng phát hiện' },
  )
  if (res) {
    showWaive.value = false
    waiveReason.value = ''; waiveEvidence.value = ''; waiveExpiry.value = ''
    await load()
  }
}

// ── Link CAPA ──
const showLinkCapa = ref(false)
const linkRef = ref('')
async function doLinkCapa() {
  if (!finding.value || !linkRef.value) return
  const res = await api.run(() => store.actionLinkToCapa(finding.value!.name, linkRef.value), {
    successMessage: 'Đã liên kết CAPA',
  })
  if (res) { showLinkCapa.value = false; linkRef.value = ''; await load() }
}

// ── Create CAPA from Finding ──
const showCreateCapa = ref(false)
const capaPayload = ref({ imm_risk_level: 'Medium', due_date: '', imm_root_cause_method: '5-Why' })
async function doCreateCapa() {
  if (!finding.value) return
  const res = await api.run(
    () => store.actionCreateCapaFromFinding(finding.value!.name, capaPayload.value),
    { successMessage: 'Đã tạo CAPA từ phát hiện' },
  )
  if (res) { showCreateCapa.value = false; await load() }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div v-if="loading" class="p-6"><SkeletonLoader variant="form" :rows="6" /></div>

    <template v-else-if="finding">
      <PageHeader
        :back-to="'/compliance/findings'"
        :title="finding.name"
        :subtitle="`IMM-16 · Theo dõi tuân thủ — Quy tắc ${finding.rule_name || finding.rule}`"
        :breadcrumb="[
          { label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' },
          { label: 'Phát hiện', to: '/compliance/findings' },
          { label: finding.name },
        ]"
      >
        <template #actions>
          <button v-if="canConfirm" class="btn-primary text-sm" @click="showConfirm = true">Xác nhận NC</button>
          <button v-if="canConfirm" class="btn-secondary text-sm" @click="showFP = true">Đánh dấu sai</button>
          <button v-if="canWaive" class="btn-ghost text-sm" @click="showWaive = true">Miễn áp dụng</button>
          <button v-if="canCreateCapa" class="btn-primary text-sm" @click="showCreateCapa = true">Tạo CAPA</button>
          <button v-if="finding.status === 'Confirmed NC' && !finding.capa_ref" class="btn-secondary text-sm" @click="showLinkCapa = true">Liên kết CAPA</button>
        </template>
      </PageHeader>

      <!-- Summary card -->
      <div class="card p-5 space-y-4">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="t-eyebrow mb-1.5">Mức độ</p>
            <StatusBadge :state="finding.severity" />
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Trạng thái</p>
            <StatusBadge :state="finding.status" />
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Ngày phát hiện</p>
            <p class="text-sm text-slate-700">{{ formatDate(finding.detected_date) }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Đánh giá ngày</p>
            <p class="text-sm text-slate-700">{{ formatDate(finding.evaluation_date) }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100">
          <div>
            <p class="t-eyebrow mb-1.5">Thiết bị</p>
            <button
              v-if="finding.asset" class="font-medium text-brand-700 hover:text-brand-800 underline-offset-2 hover:underline"
              @click="router.push(`/assets/${finding.asset}`)"
            >
              {{ formatAssetDisplay(finding.asset_name, finding.asset).main }}
            </button>
            <span v-else class="text-slate-400">—</span>
            <div
              v-if="finding.asset && formatAssetDisplay(finding.asset_name, finding.asset).hasBoth"
              class="font-mono text-xs text-brand-700 mt-0.5"
            >
              {{ formatAssetDisplay(finding.asset_name, finding.asset).sub }}
            </div>
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Khoa / phòng chịu trách nhiệm</p>
            <p class="text-sm text-slate-700">{{ finding.responsible_dept_name || finding.responsible_dept || '—' }}</p>
            <p v-if="finding.responsible_dept_name && finding.responsible_dept !== finding.responsible_dept_name" class="text-xs text-slate-400 font-mono">{{ finding.responsible_dept }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Giá trị hiện tại</p>
            <p class="text-sm text-slate-700 font-mono">{{ finding.current_value ?? '—' }}</p>
          </div>
          <div>
            <p class="t-eyebrow mb-1.5">Ngưỡng vi phạm</p>
            <p class="text-sm text-slate-700 font-mono">{{ finding.threshold_value ?? '—' }}</p>
          </div>
        </div>

        <div class="pt-4 border-t border-slate-100">
          <p class="t-eyebrow mb-1.5">CAPA liên kết</p>
          <button
            v-if="finding.capa_ref"
            class="font-mono text-sm text-brand-700 font-semibold hover:underline"
            @click="router.push(`/capas/${finding.capa_ref}`)"
          >
            {{ finding.capa_ref }}
          </button>
          <div v-else class="flex items-center gap-3">
            <span class="text-sm text-slate-400">Chưa có CAPA</span>
            <button
              v-if="canCreateCapa"
              class="btn-secondary text-xs"
              @click="showCreateCapa = true"
            >Tạo CAPA</button>
          </div>
        </div>
      </div>

      <!-- BUG-16-05: audit trail / history -->
      <RecordHistory ref-doctype="IMM Compliance Finding" :ref-name="finding.name" />
    </template>

    <!-- Confirm Modal -->
    <BaseModal v-if="showConfirm" title="Xác nhận không phù hợp (NC)" size="md" @close="showConfirm = false">
      <div class="space-y-3">
        <p class="text-sm text-slate-600">Xác nhận phát hiện này là một NC cần được CAPA xử lý.</p>
        <div class="form-group">
          <label class="form-label">Ghi chú người đánh giá</label>
          <textarea v-model="reviewerNote" rows="4" class="form-input" placeholder="Mô tả ngữ cảnh xác nhận..." />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showConfirm = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="doConfirm">Xác nhận NC</button>
      </template>
    </BaseModal>

    <!-- False Positive Modal -->
    <BaseModal v-if="showFP" title="Đánh dấu sai" size="md" @close="showFP = false">
      <div class="space-y-3">
        <div class="form-group">
          <label class="form-label">Lý do (≥ 10 ký tự) *</label>
          <textarea v-model="fpReason" rows="4" class="form-input" />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showFP = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="doFP">Đánh dấu sai</button>
      </template>
    </BaseModal>

    <!-- Waive Modal -->
    <BaseModal v-if="showWaive" title="Miễn áp dụng" size="lg" @close="showWaive = false">
      <div class="space-y-3">
        <p class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
          Chỉ vai trò có quyền (BR-16-06) mới được waive. Hành động này được ghi vào audit trail.
        </p>
        <div class="form-group">
          <label class="form-label">Lý do miễn (≥ 50 ký tự) *</label>
          <textarea v-model="waiveReason" rows="5" class="form-input" />
          <p class="text-xs text-slate-400 mt-1">{{ waiveReason.length }} ký tự</p>
        </div>
        <div class="form-group">
          <label class="form-label">URL bằng chứng *</label>
          <input v-model="waiveEvidence" class="form-input" placeholder="https://..." />
        </div>
        <div class="form-group">
          <label class="form-label">Ngày hết hiệu lực *</label>
          <input v-model="waiveExpiry" type="date" class="form-input" />
          <p class="text-xs text-slate-400 mt-1">Sau ngày này, phát hiện sẽ tự động mở lại.</p>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showWaive = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="doWaive">Xác nhận miễn áp dụng</button>
      </template>
    </BaseModal>

    <!-- Link CAPA Modal -->
    <BaseModal v-if="showLinkCapa" title="Liên kết CAPA" size="md" @close="showLinkCapa = false">
      <div class="form-group">
        <label class="form-label">Mã CAPA *</label>
        <input v-model="linkRef" class="form-input" placeholder="CAPA-2026-00001" />
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showLinkCapa = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="doLinkCapa">Liên kết</button>
      </template>
    </BaseModal>

    <!-- Create CAPA Modal -->
    <BaseModal v-if="showCreateCapa" title="Tạo CAPA từ phát hiện" size="md" @close="showCreateCapa = false">
      <div class="space-y-3">
        <div class="form-group">
          <label class="form-label">Mức rủi ro</label>
          <select v-model="capaPayload.imm_risk_level" class="form-select">
            <option value="Low">Thấp</option>
            <option value="Medium">Trung bình</option>
            <option value="High">Cao</option>
            <option value="Critical">Nghiêm trọng</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Phương pháp phân tích gốc</label>
          <select v-model="capaPayload.imm_root_cause_method" class="form-select">
            <option value="5-Why">5-Why</option>
            <option value="Fishbone">Fishbone</option>
            <option value="FTA">FTA</option>
            <option value="Pareto">Pareto</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Hạn xử lý</label>
          <input v-model="capaPayload.due_date" type="date" class="form-input" />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showCreateCapa = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="doCreateCapa">Tạo CAPA</button>
      </template>
    </BaseModal>
  </div>
</template>
