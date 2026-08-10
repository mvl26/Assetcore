<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-14 · Giải nhiệm thiết bị (End-of-Life) — Chi tiết & DUYỆT biên bản giải nhiệm.
//
// Bề mặt thu hồi hồ sơ draft mồ côi: hồ sơ Asset Decommission docstatus=0 (tạo
// thành công nhưng chưa duyệt, vd approve 403 create-only) reachable qua route này
// và duyệt được bởi approver — tách CREATE ≠ APPROVE (GATE-8/LL-FE-51).
//
// CTA "Duyệt giải nhiệm" 100% SERVER-DRIVEN: chỉ render khi `record.can_approve===1`
// (BE dẫn xuất từ CÙNG SoT mà approve_decommission enforce) — TUYỆT ĐỐI KHÔNG
// hardcode docstatus/workflow_state===. can_approve=0/undefined → KHÔNG render nút,
// hiện hint `approve_blocked_reason` (no dead-control, LL-FE-47).
//
// 4-layer: view → useApi → api/imm14 → frappeGet/frappePost. Nhãn 100% tiếng Việt
// qua SSoT (StatusBadge domain-specific + disposalMethodLabel + riskClassificationLabel);
// KHÔNG rò asset-id thô / User-email thô (LL-FE-53 / user_source policy).
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
import { getDecommission, approveDecommission, type DecommissionRecord } from '@/api/imm14'
import PageHeader from '@/components/common/PageHeader.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'
import {
  disposalMethodLabel,
  decommissionStateLabel,
  decommissionStateClass,
  riskClassificationLabel,
} from '@/constants/labels'
import { formatDate } from '@/utils/formatters'

const props = defineProps<{ id: string }>()

const router = useRouter()
const api = useApi()
const notify = useNotify()

const record = ref<DecommissionRecord | null>(null)
const loading = ref(true)                        // INV-UX4-8 — chống nháy 404 một nhịp
// Lỗi của LƯỢT NẠP — giữ NGUYÊN đối tượng `ApiError` để `useDetailAccess` phân loại kind
// (mạng / 403-in-envelope / 404), thay bản `loadErrorKind` cục bộ (AC-UX-053).
const loadError = ref<unknown>(null)
const { kind: loadKind, message: loadMsg } = useDetailAccess(() => loadError.value)

async function load() {
  loadError.value = null                         // INV-UX4-7 — xoá lỗi ở DÒNG ĐẦU
  loading.value = true
  try {
    const res = await api.run(() => getDecommission(props.id), {
      silentSuccess: true,
      silentError: true,
    })
    if (res) {
      record.value = res
    } else {
      // `api.run` NUỐT lỗi (silentError) ⇒ chỉ `api.lastError` mới nói được đây là lỗi THẬT.
      // Không có lỗi mà vẫn rỗng = bản ghi không tồn tại ⇒ để shell rẽ nhánh `notfound`,
      // KHÔNG bịa một lỗi `unknown` (sẽ mời «Thử lại» cho một mã vĩnh viễn không có).
      loadError.value = api.lastError.value ?? null
      record.value = null                        // dọn ảnh chụp cũ
    }
  } finally {
    loading.value = false
  }
}

// ── Cổng duyệt server-driven (GATE-8/LL-FE-51) ──────────────────────────────────
// CTA chỉ theo cờ BE `can_approve===1`; KHÔNG suy từ docstatus/workflow_state thô.
const canApprove = computed(() => record.value?.can_approve === 1)
const approveBlockedReason = computed(() => record.value?.approve_blocked_reason ?? '')
// Hint chỉ hiện khi KHÔNG có CTA và BE nêu lý do (rỗng ⇒ không phô hint thừa).
const showNoActionsHint = computed(
  () => !canApprove.value && approveBlockedReason.value.trim().length > 0,
)

// ── Hiển thị (nhãn VI qua SSoT) ─────────────────────────────────────────────────
const assetDisplayName = computed(
  () => record.value?.asset_name || record.value?.asset_name_snapshot || '—',
)
const responsibleDisplay = computed(() => record.value?.responsible_name || '—')
const disposalLabel = computed(() => disposalMethodLabel(record.value?.disposal_method))
const stateLabel = computed(() => decommissionStateLabel(record.value?.workflow_state))
const stateClass = computed(() => decommissionStateClass(record.value?.workflow_state))
const patientDataDone = computed(() => !!record.value?.patient_data_sanitized)
const riskLabel = computed(() =>
  record.value?.risk_classification_snapshot
    ? riskClassificationLabel(record.value.risk_classification_snapshot)
    : '—',
)

async function approve() {
  const rec = record.value
  if (!rec || !canApprove.value) return
  const ok = await notify.confirm({
    title: 'Duyệt giải nhiệm thiết bị',
    body:
      `Xác nhận duyệt hồ sơ giải nhiệm ${rec.name}? Thiết bị "${assetDisplayName.value}" `
      + 'sẽ chuyển sang trạng thái Đã thanh lý và không thể hoàn tác.',
    confirmText: 'Duyệt giải nhiệm',
    cancelText: 'Huỷ',
  })
  if (!ok) return
  const res = await api.run(() => approveDecommission(rec.name), {
    silentSuccess: true,
    silentError: true,
  })
  if (res) {
    notify.show({ code: MSG.IMM14_APPROVE_SUCCESS, ctx: { asset: res.asset, name: res.name } })
    // Refetch → can_approve về 0, CTA tự ẩn, badge đổi "Đã giải nhiệm".
    await load()
  } else {
    notify.fromError(api.lastError.value)
  }
}

function goAsset() {
  if (record.value?.asset) router.push(`/assets/${record.value.asset}`)
}

onMounted(load)
</script>

<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadKind"
    :error-message="loadMsg"
    :doc="record"
    entity-label="hồ sơ giải nhiệm"
    :record-id="props.id"
    back-label="Về danh sách giải nhiệm"
    @retry="load()"
    @back="router.push('/decommissions')">
    <template #title>
      <PageHeader
        back-to="/decommissions"
        back-label="← Biên bản giải nhiệm"
        title="Hồ sơ giải nhiệm"
        :subtitle="record ? `Số hồ sơ: ${record.name}` : ''"
        :breadcrumb="[
          { label: 'IMM-14 · Giải nhiệm thiết bị' },
          { label: 'Biên bản giải nhiệm', to: '/decommissions' },
          { label: record?.name || id },
        ]"
      />
    </template>

    <!-- CTA duyệt (server-driven `can_approve`) — CHỈ tồn tại ở trạng thái content. -->
    <template #actions>
      <button
        class="text-sm text-brand-600 hover:text-brand-700 font-medium underline focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
        data-testid="cta-open-asset"
        aria-label="Mở hồ sơ thiết bị liên quan"
        @click="goAsset"
      >Xem hồ sơ thiết bị →</button>

      <div class="ml-auto flex items-center gap-3">
        <div v-if="canApprove" class="flex flex-col items-end gap-1">
          <button
            class="btn-primary text-sm focus-visible:ring-2 focus-visible:ring-emerald-500"
            data-testid="cta-approve"
            aria-describedby="cta-approve-desc"
            :disabled="api.loading.value"
            @click="approve"
          >Duyệt giải nhiệm</button>
          <p id="cta-approve-desc" class="text-xs text-slate-400">
            Duyệt sẽ chuyển thiết bị sang trạng thái Đã thanh lý (không thể hoàn tác).
          </p>
        </div>
        <!-- Không đủ điều kiện duyệt → hint lý do (no dead-control). -->
        <p
          v-else-if="showNoActionsHint"
          class="text-sm text-slate-500 italic max-w-md text-right"
          data-testid="no-actions-hint"
          role="note"
        >{{ approveBlockedReason }}</p>
      </div>
    </template>

    <template v-if="record">
      <!-- Header hồ sơ + badge trạng thái -->
      <div class="card p-5 mb-5">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p class="text-xs text-slate-400">Thiết bị</p>
            <h2 class="text-lg font-semibold text-slate-800">{{ assetDisplayName }}</h2>
          </div>
          <span
            class="inline-flex items-center font-medium rounded-full px-3 py-1 text-xs leading-none whitespace-nowrap"
            :class="stateClass"
            data-testid="decom-state-badge"
          >{{ stateLabel }}</span>
        </div>
      </div>

      <!-- Chi tiết biên bản -->
      <div class="card p-5 mb-5">
        <dl class="grid gap-x-6 gap-y-4 sm:grid-cols-2 text-sm">
          <div>
            <dt class="text-slate-400 mb-0.5">Phương thức xử lý</dt>
            <dd class="text-slate-700" data-testid="decom-disposal">{{ disposalLabel }}</dd>
          </div>
          <div>
            <dt class="text-slate-400 mb-0.5">Người chịu trách nhiệm</dt>
            <dd class="text-slate-700" data-testid="decom-responsible">{{ responsibleDisplay }}</dd>
          </div>
          <div>
            <dt class="text-slate-400 mb-0.5">Phân loại rủi ro</dt>
            <dd class="text-slate-700">{{ riskLabel }}</dd>
          </div>
          <div>
            <dt class="text-slate-400 mb-0.5">Ngày giải nhiệm</dt>
            <dd class="text-slate-700">{{ formatDate(record.decommissioned_on) || '—' }}</dd>
          </div>
          <div class="sm:col-span-2">
            <dt class="text-slate-400 mb-0.5">Xử lý dữ liệu bệnh nhân</dt>
            <dd class="text-slate-700" data-testid="decom-patient-data">
              <span :class="patientDataDone ? 'text-emerald-700' : 'text-amber-700'">
                {{ patientDataDone ? 'Đã xử lý' : 'Chưa xử lý' }}
              </span>
              <span v-if="record.sanitization_note" class="text-slate-500">
                — {{ record.sanitization_note }}
              </span>
            </dd>
          </div>
          <div class="sm:col-span-2">
            <dt class="text-slate-400 mb-0.5">Lý do giải nhiệm</dt>
            <dd class="text-slate-700 whitespace-pre-line">{{ record.decommission_reason || '—' }}</dd>
          </div>
        </dl>
      </div>
    </template>
  </DetailPageShell>
</template>
