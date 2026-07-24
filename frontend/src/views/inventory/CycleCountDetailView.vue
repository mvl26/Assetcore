<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-15 · Chi tiết phiếu kiểm kê tồn kho (Cycle Count) + workflow.
//
// GATE-8 / LL-FE-51: nút hành động (Submit / Recount / Post) render THEO
// `allowed_transitions` do BE emit (server-driven CTA) — KHÔNG hardcode
// `status === 'X'`. FE gate = allowedTransitions.includes('<Action>').
//   'Submit'  → Gửi rà soát        (Planned/Counting → Reviewed)
//   'Recount' → Sửa đếm lại        (Reviewed → Counting — gửi về đếm lại)
//   'Post'    → Ghi nhận điều chỉnh (Reviewed → Posted)
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm15Store } from '@/stores/imm15'
import { submitCycleCount, postCycleCount, recountCycleCount } from '@/api/imm15'
import type { CycleCountItem } from '@/api/imm15'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import WorkflowStepper from '@/components/common/WorkflowStepper.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import DetailLoadError from '@/components/common/DetailLoadError.vue'
import { loadErrorKind } from '@/api/errors'
import { useApi } from '@/composables/useApi'
import { formatCurrency, formatDate } from '@/utils/formatters'
import {
  cycleCountTypeLabel, cycleCountStateLabel,
  CYCLE_COUNT_ROOT_CAUSE_OPTIONS,
} from '@/constants/cycleCountLabels'

const CYCLE_STEPS = ['Planned', 'Counting', 'Reviewed', 'Posted']

const route = useRoute()
const router = useRouter()
const store = useImm15Store()
const api = useApi()
const { cycleCountDetail, cycleCountDetailLoading, error, lastApiError } = storeToRefs(store)

const name = computed(() => route.params.name as string)
const detail = computed(() => cycleCountDetail.value)
// Mã phiếu kiểm kê sai / đã xoá ⇒ 404: empty-state "không tìm thấy" + lối về danh
// sách (trước chỉ có nút "Thử lại" — vô nghĩa với mã sai, và không có lối thoát).
const loadFailed = computed<'' | 'notfound' | 'unknown'>(() =>
  detail.value ? '' : (error.value ? loadErrorKind(lastApiError.value) : ''))
const status = computed(() => detail.value?.status ?? '')
const items = computed<CycleCountItem[]>(() => detail.value?.items ?? [])

// Server-driven CTA (KHÔNG hardcode status===).
const allowedTransitions = computed(() => detail.value?.allowed_transitions ?? [])
const canSubmit = computed(() => allowedTransitions.value.includes('Submit'))
const canRecount = computed(() => allowedTransitions.value.includes('Recount'))
const canPost = computed(() => allowedTransitions.value.includes('Post'))

const isEditable = computed(() => canSubmit.value)  // Planned/Counting → nhập số đếm
const showVariance = computed(() =>
  status.value === 'Reviewed' || status.value === 'Posted')
const capaCount = computed(() => detail.value?.capa_created ?? 0)
const adjustmentRef = computed(() => detail.value?.adjustment_ref || '')

// Số đếm + nguyên nhân nhập tay theo dòng (khoá theo spare_part).
const counted = reactive<Record<string, number>>({})
const rootCause = reactive<Record<string, string>>({})

function seedInputs() {
  for (const it of items.value) {
    if (!(it.spare_part in counted)) counted[it.spare_part] = it.counted_qty ?? 0
    if (!(it.spare_part in rootCause)) rootCause[it.spare_part] = it.root_cause ?? ''
  }
}
watch(items, seedInputs, { immediate: true })

async function load() {
  await store.fetchCycleCount(name.value)
}

// ── Submit (Planned/Counting → Reviewed) ──────────────────────────────────
const submitting = ref(false)
async function doSubmit() {
  submitting.value = true
  const payload = items.value.map(it => ({
    spare_part: it.spare_part,
    counted_qty: Number(counted[it.spare_part] ?? 0),
    root_cause: rootCause[it.spare_part] || undefined,
  }))
  const res = await api.run(() => submitCycleCount(name.value, payload), {
    successMessage: 'Đã gửi rà soát — phiếu chuyển trạng thái Đã rà soát',
  })
  submitting.value = false
  if (res) await load()
}

// ── Post (Reviewed → Posted) ──────────────────────────────────────────────
const showPostModal = ref(false)
const verifiedBy = ref<string | undefined>(undefined)
const posting = ref(false)
async function doPost() {
  posting.value = true
  const res = await api.run(() => postCycleCount(name.value, verifiedBy.value || '', ''), {
    successMessage: 'Đã ghi nhận điều chỉnh tồn — phiếu Đã ghi nhận',
  })
  posting.value = false
  if (res) {
    showPostModal.value = false
    await load()
  }
}

// ── Recount / Sửa đếm lại (Reviewed → Counting) ──────────────────────────
const showRecountModal = ref(false)
const recountReason = ref('')
const recounting = ref(false)
function openRecountModal() {
  recountReason.value = ''
  showRecountModal.value = true
}
async function doRecount() {
  const reason = recountReason.value.trim()
  if (!reason) return   // BE cũng validate; nút Xác nhận đã disabled khi rỗng.
  recounting.value = true
  const res = await api.run(() => recountCycleCount(name.value, reason), {
    successMessage: 'Đã gửi phiếu về Đang kiểm đếm để đếm lại',
  })
  recounting.value = false
  if (res) {
    showRecountModal.value = false
    await load()
  }
}

function variancePctText(it: CycleCountItem): string {
  const v = it.variance_pct
  if (v == null) return '—'
  return `${Number(v).toFixed(1)}%`
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      :title="`Phiếu kiểm kê ${name}`"
      subtitle="IMM-15 · Tồn kho phụ tùng — Kiểm kê tồn kho"
      :breadcrumb="[
        { label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory' },
        { label: 'Kiểm kê tồn kho', to: '/inventory/cycle-counts' },
        { label: name },
      ]"
    >
      <template #actions>
        <button class="btn-secondary" @click="router.push({ name: 'CycleCountList' })">Quay lại</button>
      </template>
    </PageHeader>

    <!-- Tri-branch loading / error / content -->
    <div v-if="cycleCountDetailLoading && !detail" class="card p-6">
      <SkeletonLoader variant="table" :rows="5" />
    </div>
    <DetailLoadError
      v-else-if="loadFailed"
      :kind="loadFailed"
      entity-label="phiếu kiểm kê"
      :record-id="name"
      :message="error ?? ''"
      back-label="Về danh sách kiểm kê"
      @retry="load()"
      @back="router.push('/inventory/cycle-counts')"
    />

    <template v-else-if="detail">
      <!-- Header + workflow -->
      <div class="card p-5 space-y-4">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <dl class="grid grid-cols-2 sm:grid-cols-3 gap-x-8 gap-y-3 text-sm">
            <div>
              <dt class="text-xs text-slate-400">Kho</dt>
              <dd class="text-slate-800 font-medium">{{ detail.warehouse_name || detail.warehouse }}</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Loại kiểm kê</dt>
              <dd class="text-slate-800">{{ cycleCountTypeLabel(detail.count_type) }}</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Ngày kiểm kê</dt>
              <dd class="text-slate-800">{{ formatDate(detail.count_date) }}</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Người kiểm</dt>
              <dd class="text-slate-800">{{ detail.counted_by_name || detail.counted_by || '—' }}</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Người xác nhận</dt>
              <dd class="text-slate-800">{{ detail.verified_by_name || detail.verified_by || '—' }}</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Trạng thái</dt>
              <dd><StatusBadge :state="detail.status" /></dd>
            </div>
          </dl>

          <!-- Workflow CTA (server-driven, KHÔNG hardcode status===) -->
          <div class="flex gap-2 flex-wrap">
            <button
              v-if="canSubmit"
              data-testid="cta-submit"
              class="btn-primary"
              :disabled="submitting"
              @click="doSubmit"
            >{{ submitting ? 'Đang gửi…' : 'Gửi rà soát' }}</button>
            <button
              v-if="canRecount"
              data-testid="cta-recount"
              class="bg-amber-700 hover:bg-amber-800 text-white px-4 py-2 rounded-lg text-sm font-medium focus-visible:ring-2 focus-visible:ring-amber-500"
              @click="openRecountModal"
            >Sửa đếm lại</button>
            <button
              v-if="canPost"
              data-testid="cta-post"
              class="bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-2 rounded-lg text-sm font-medium focus-visible:ring-2 focus-visible:ring-emerald-500"
              @click="showPostModal = true"
            >Ghi nhận điều chỉnh</button>
          </div>
        </div>

        <WorkflowStepper :steps="CYCLE_STEPS" :current="detail.status" :label-for="cycleCountStateLabel" />
      </div>

      <!-- Kết quả sau khi ghi nhận: bút toán điều chỉnh + cảnh báo CAPA -->
      <div v-if="status === 'Posted'" class="space-y-3">
        <div v-if="adjustmentRef" class="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 flex items-center justify-between">
          <span>Đã tạo bút toán điều chỉnh tồn:
            <button class="font-mono font-semibold underline hover:text-emerald-900 focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
                    @click="router.push(`/stock-movements/${adjustmentRef}`)">{{ adjustmentRef }}</button>
          </span>
        </div>
        <div v-if="capaCount > 0" class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p class="font-medium">Có {{ capaCount }} dòng lệch vượt ngưỡng — đã phát sinh hành động khắc phục/phòng ngừa (CAPA).</p>
          <button class="btn-secondary mt-2" @click="router.push('/capas')">Xem danh sách CAPA</button>
        </div>
      </div>

      <!-- Summary variance -->
      <div v-if="showVariance" class="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div class="card p-4">
          <p class="text-xs text-slate-400">Số dòng lệch</p>
          <p class="text-xl font-semibold" :class="(detail.variance_count ?? 0) > 0 ? 'text-amber-700' : 'text-slate-700'">{{ detail.variance_count ?? 0 }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-slate-400">Giá trị lệch</p>
          <p class="text-xl font-semibold text-slate-700 tabular-nums">{{ formatCurrency(detail.variance_value) }}</p>
        </div>
      </div>

      <!-- Item lines -->
      <div class="card overflow-hidden">
        <div class="px-4 py-3 border-b border-slate-100 text-sm font-medium text-slate-700">Dòng kiểm kê</div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b border-slate-100">
              <tr>
                <th class="table-header">Phụ tùng</th>
                <th class="table-header text-right">SL hệ thống</th>
                <th class="table-header text-right">SL đếm thực tế</th>
                <th v-if="showVariance" class="table-header text-right">Chênh lệch</th>
                <th v-if="showVariance" class="table-header text-right hidden md:table-cell">Giá trị lệch</th>
                <th class="table-header hidden lg:table-cell">Nguyên nhân</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-50">
              <tr v-for="(it, idx) in items" :key="it.spare_part">
                <td class="px-4 py-3 text-slate-800">
                  {{ it.part_name || it.spare_part }}
                  <span class="block text-[11px] font-mono text-slate-400">{{ it.spare_part }}</span>
                </td>
                <td class="px-4 py-3 text-right tabular-nums text-slate-600">{{ it.system_qty }}</td>
                <td class="px-4 py-3 text-right">
                  <input
                    v-if="isEditable"
                    v-model.number="counted[it.spare_part]"
                    type="number"
                    min="0"
                    step="any"
                    class="form-input w-24 text-right"
                    :aria-label="`Số đếm thực tế cho ${it.part_name || it.spare_part}`"
                  />
                  <span v-else class="tabular-nums text-slate-800">{{ it.counted_qty }}</span>
                </td>
                <td v-if="showVariance" class="px-4 py-3 text-right tabular-nums"
                    :class="(it.variance_qty ?? 0) !== 0 ? 'text-amber-700 font-semibold' : 'text-slate-500'">
                  {{ it.variance_qty ?? 0 }}
                  <span class="block text-[11px] text-slate-400">{{ variancePctText(it) }}</span>
                </td>
                <td v-if="showVariance" class="px-4 py-3 text-right tabular-nums text-slate-600 hidden md:table-cell">{{ formatCurrency(it.variance_value) }}</td>
                <td class="px-4 py-3 hidden lg:table-cell">
                  <select
                    v-if="isEditable"
                    v-model="rootCause[it.spare_part]"
                    class="form-select text-xs"
                    :aria-label="`Nguyên nhân lệch cho ${it.part_name || it.spare_part}`"
                  >
                    <option value="">—</option>
                    <option v-for="o in CYCLE_COUNT_ROOT_CAUSE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
                  </select>
                  <span v-else class="text-xs text-slate-500">{{ it.root_cause || '—' }}</span>
                  <span class="sr-only">{{ idx }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Post modal: chọn người xác nhận (khác người kiểm — segregation) -->
    <BaseModal v-if="showPostModal" title="Ghi nhận điều chỉnh tồn" @close="showPostModal = false">
      <div class="space-y-4">
        <p class="text-sm text-slate-600">
          Ghi nhận sẽ tạo bút toán điều chỉnh tồn theo chênh lệch đã rà soát và không thể hoàn tác.
          Người xác nhận phải khác người kiểm kê.
        </p>
        <div class="form-group">
          <label class="form-label" for="cc-verifier">Người xác nhận</label>
          <ApproverSelect id="cc-verifier" v-model="verifiedBy" context="user" />
        </div>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="showPostModal = false">Hủy</button>
        <button class="btn-primary" :disabled="posting" @click="doPost">
          {{ posting ? 'Đang ghi nhận…' : 'Xác nhận ghi nhận' }}
        </button>
      </template>
    </BaseModal>

    <!-- Recount modal: gửi phiếu đã rà soát về Đang kiểm đếm để đếm lại. -->
    <BaseModal v-if="showRecountModal" title="Sửa đếm lại" @close="showRecountModal = false">
      <div class="space-y-4">
        <p class="text-sm text-slate-600">
          Gửi phiếu về trạng thái Đang kiểm đếm để kiểm đếm lại. Số đếm và chênh lệch đã rà soát
          sẽ mở lại để chỉnh sửa. Vui lòng nêu rõ lý do đếm lại (bắt buộc).
        </p>
        <div class="form-group">
          <label class="form-label" for="cc-recount-reason">Lý do đếm lại</label>
          <textarea
            id="cc-recount-reason"
            data-testid="recount-reason"
            v-model="recountReason"
            rows="3"
            required
            aria-required="true"
            :aria-describedby="!recountReason.trim() ? 'cc-recount-reason-hint' : undefined"
            class="form-input w-full"
            placeholder="Ví dụ: chênh lệch bất thường tại kệ A3, cần kiểm đếm lại"
          ></textarea>
          <p v-if="!recountReason.trim()" id="cc-recount-reason-hint" class="text-xs text-slate-400 mt-1">
            Bắt buộc nhập lý do trước khi gửi về đếm lại.
          </p>
        </div>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="showRecountModal = false">Hủy</button>
        <button
          class="btn-primary"
          data-testid="cta-recount-confirm"
          :disabled="recounting || !recountReason.trim()"
          @click="doRecount"
        >{{ recounting ? 'Đang gửi…' : 'Xác nhận đếm lại' }}</button>
      </template>
    </BaseModal>
  </div>
</template>
