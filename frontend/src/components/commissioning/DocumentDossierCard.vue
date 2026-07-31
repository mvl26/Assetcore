<script setup lang="ts">
/**
 * Thẻ "Trạng thái hồ sơ pháp lý" của thiết bị — consumer IMM-04 của IMM-05
 * `get_asset_documents` (CR-75, docs/imm-05/06_Frontend_Design.md §4.4).
 *
 * Presentational thuần: KHÔNG fetch, KHÔNG store, KHÔNG so ngày bằng đồng hồ máy.
 * Mọi kết luận tuân thủ đến từ khoá SỐ `is_compliant` của server (SSoT
 * overdue-server-flag); `documentStatus` chỉ dùng để CHỌN NHÃN và tách sắc thái
 * "sắp hết hạn" (cảnh báo) khỏi "đủ" — KHÔNG bao giờ dùng để gate.
 */
import { computed } from 'vue'
import { dossierStatusLabel, docCategoryLabel } from '@/constants/labels'
import { stateLabel } from '@/utils/docUtils'
import { formatFileSize } from '@/utils/formatters'
import type { AssetDossierDocItem } from '@/api/imm05'

const props = withDefaults(
  defineProps<{
    /**
     * Dòng hồ sơ đã LỌC QUYỀN của server (`documents[doc_category][]`).
     * Presentational: nhận sao render vậy — hồ sơ bị ẩn không tới đây (BR-05-20)
     * nên `file_url` của nó cũng không bao giờ có mặt.
     */
    documents?: Record<string, AssetDossierDocItem[]>
    /** Enum SSoT 5 giá trị; `null`/lạ ⇒ nhãn "Chưa có dữ liệu". */
    documentStatus?: string | null
    /** `is_compliant` của server: true/false; `null` = CHƯA BIẾT ⇒ không kết tội. */
    isCompliant?: boolean | null
    completenessPct?: number | null
    requiredTotal?: number | null
    requiredSatisfied?: number | null
    missingRequired?: string[]
    expiredRequired?: string[]
    expiringRequired?: string[]
    hiddenCount?: number
  }>(),
  {
    documents: () => ({}),
    documentStatus: null,
    isCompliant: null,
    completenessPct: 0,
    requiredTotal: null,
    requiredSatisfied: null,
    missingRequired: () => [],
    expiredRequired: () => [],
    expiringRequired: () => [],
    hiddenCount: 0,
  },
)

const emit = defineEmits<{ (e: 'refresh'): void }>()

/**
 * Server CHƯA nói (đang tải / BE chưa deploy CR-75). Không kết tội (không đỏ)
 * nhưng cũng KHÔNG khoe xanh: tô trung tính và giấu thanh % vì chính con số %
 * lúc đó cũng không đáng tin (hợp đồng cũ trả hằng 0 → "0% đầy đủ" là nói dối).
 */
const unknown = computed(() => props.isCompliant === null || props.isCompliant === undefined)

/** Chưa biết ⇒ coi như hợp lệ để không nháy đỏ giả (06 §4.4 điểm 1). */
const compliant = computed(() => props.isCompliant !== false)

/** Vàng CHỈ khi vẫn tuân thủ mà sắp hết hạn — cảnh báo, không chặn. */
const isExpiringTone = computed(
  () => compliant.value && !unknown.value && props.documentStatus === 'Expiring_Soon',
)

const statusLabel = computed(() => dossierStatusLabel(props.documentStatus))

const pct = computed(() => {
  const raw = Number(props.completenessPct ?? 0)
  if (!Number.isFinite(raw)) return 0
  return Math.min(100, Math.max(0, Math.round(raw)))
})

/** Mẫu số rỗng: nhóm thiết bị không có loại hồ sơ bắt buộc nào áp dụng. */
const noRequiredTypes = computed(() => props.requiredTotal === 0)
const hasDenominator = computed(
  () => typeof props.requiredTotal === 'number' && typeof props.requiredSatisfied === 'number',
)

const cardClass = computed(() => {
  if (!compliant.value) return 'bg-red-50 border-red-200'
  if (unknown.value) return 'bg-slate-50 border-slate-200'
  if (isExpiringTone.value) return 'bg-amber-50 border-amber-200'
  return 'bg-emerald-50 border-emerald-200'
})
const badgeClass = computed(() => {
  if (!compliant.value) return 'bg-red-100 text-red-800'
  if (unknown.value) return 'bg-slate-200 text-slate-700'
  if (isExpiringTone.value) return 'bg-amber-100 text-amber-800'
  return 'bg-emerald-100 text-emerald-800'
})
const barClass = computed(() => {
  if (!compliant.value) return 'bg-red-500'
  if (isExpiringTone.value) return 'bg-amber-500'
  return 'bg-emerald-500'
})

// ─── Danh sách hồ sơ + tệp đính kèm (AC-CR-81) ──────────────────────────────

interface DossierGroup {
  category: string
  label: string
  rows: AssetDossierDocItem[]
}

/** Nhóm KHÔNG rỗng, sắp theo nhãn tiếng Việt để thứ tự hiển thị ổn định. */
const groups = computed<DossierGroup[]>(() =>
  Object.entries(props.documents ?? {})
    .filter(([, rows]) => Array.isArray(rows) && rows.length > 0)
    .map(([category, rows]) => ({ category, label: docCategoryLabel(category), rows }))
    .sort((a, b) => a.label.localeCompare(b.label, 'vi')),
)

const hasRows = computed(() => groups.value.length > 0)

/**
 * Ba trạng thái tệp — `has_file` của server là khoá QUYẾT ĐỊNH duy nhất:
 *  - `'yes'`     : có tệp thật ⇒ được phép phát link;
 *  - `'no'`      : server khẳng định KHÔNG có tệp (kể cả link mồ côi đã bị khử);
 *  - `'unknown'` : BE chưa deploy AC-CR-81 ⇒ chưa biết, KHÔNG vu "chưa đính kèm".
 *
 * Phòng thủ 2 lớp: `'yes'` còn đòi `file_url` non-empty — FE không tự bịa link
 * từ lời hứa của hợp đồng.
 */
function fileState(row: AssetDossierDocItem): 'yes' | 'no' | 'unknown' {
  if (row.has_file === undefined || row.has_file === null) return 'unknown'
  return Number(row.has_file) === 1 && !!row.file_url ? 'yes' : 'no'
}

/** Tên tệp + kích thước đọc-được. KHÔNG bao giờ trả URL thô. */
function fileMeta(row: AssetDossierDocItem): string {
  const size = formatFileSize(row.file_size)
  const name = row.file_name || 'Tệp đính kèm'
  return size ? `${name} · ${size}` : name
}

function docTitle(row: AssetDossierDocItem): string {
  return row.doc_type_detail || row.doc_category || row.name
}
</script>

<template>
  <div class="rounded-lg border p-4" :class="cardClass" data-testid="dossier-card">
    <div class="flex items-center justify-between gap-3 mb-2">
      <span class="text-sm font-semibold text-slate-700">Trạng thái hồ sơ pháp lý</span>
      <!-- Nhãn CHỮ luôn đi kèm màu (WCAG 2.1 AA — không phân biệt chỉ bằng màu) -->
      <span
        class="text-xs font-bold px-2 py-0.5 rounded-full"
        :class="badgeClass"
        data-testid="dossier-status"
      >{{ statusLabel }}</span>
    </div>

    <!-- Server chưa cấp số liệu ⇒ nói "chưa biết", KHÔNG vẽ thanh 0% (nói dối) -->
    <p v-if="unknown" class="text-xs text-slate-600" data-testid="dossier-unknown">
      Chưa lấy được số liệu mức đầy đủ hồ sơ của thiết bị này.
    </p>

    <!-- Mẫu số rỗng: nói thẳng, KHÔNG khoe 100% (BR-05-17) -->
    <p
      v-else-if="noRequiredTypes"
      class="text-xs text-slate-600"
      data-testid="dossier-no-required"
    >
      Không có loại hồ sơ bắt buộc áp dụng cho nhóm thiết bị này.
    </p>

    <!-- Mức đầy đủ: số THẬT + mẫu số minh bạch -->
    <div v-else class="flex items-center gap-3 mb-2">
      <div
        class="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden"
        role="progressbar"
        :aria-valuenow="pct"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`Mức đầy đủ hồ sơ pháp lý ${pct}%`"
      >
        <div class="h-full rounded-full transition-all" :class="barClass" :style="{ width: `${pct}%` }" />
      </div>
      <span class="text-xs text-slate-600 whitespace-nowrap" data-testid="dossier-pct">
        {{ pct }}%
        <span v-if="hasDenominator" class="text-slate-500">
          ({{ requiredSatisfied }}/{{ requiredTotal }} loại bắt buộc)
        </span>
      </span>
    </div>

    <!-- ĐÃ QUÁ HẠN ⇒ hành động GIA HẠN (tách khỏi "thiếu" — hai việc khác nhau) -->
    <div v-if="expiredRequired.length" class="mt-2" data-testid="dossier-expired">
      <p class="text-xs text-red-700 font-medium mb-1">
        Hết hạn: {{ expiredRequired.join(', ') }}
      </p>
      <p class="text-xs text-red-600">Cần gia hạn/cấp lại trước khi tiếp tục sử dụng thiết bị.</p>
    </div>

    <!-- CHƯA CÓ ⇒ hành động BỔ SUNG MỚI -->
    <div v-if="missingRequired.length" class="mt-2" data-testid="dossier-missing">
      <p class="text-xs text-red-700 font-medium mb-1">Thiếu hồ sơ bắt buộc:</p>
      <ul class="text-xs text-red-600 space-y-0.5 list-disc list-inside">
        <li v-for="m in missingRequired" :key="m">{{ m }}</li>
      </ul>
    </div>

    <!-- SẮP HẾT HẠN ⇒ cảnh báo, KHÔNG chặn -->
    <p
      v-if="expiringRequired.length"
      class="mt-2 text-xs text-amber-700"
      data-testid="dossier-expiring"
    >
      Sắp hết hạn: {{ expiringRequired.join(', ') }}
    </p>

    <!--
      Danh sách hồ sơ + TỆP THẬT (AC-CR-81). Trước đây thẻ chỉ nói "đủ/thiếu" mà
      không có lối mở tệp ⇒ người dùng phải đi đường vòng. `has_file` quyết định
      link; link mồ côi đã bị BE khử nên UI KHÔNG bao giờ phát đường dẫn chết.
    -->
    <div v-if="hasRows" class="mt-3 border-t border-slate-200/70 pt-2" data-testid="dossier-doc-list">
      <p class="text-xs font-semibold text-slate-700 mb-1">Hồ sơ đã có</p>
      <div v-for="g in groups" :key="g.category" class="mb-2 last:mb-0">
        <p class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">{{ g.label }}</p>
        <ul class="space-y-1">
          <li
            v-for="row in g.rows"
            :key="row.name"
            class="flex flex-wrap items-center justify-between gap-2 rounded bg-white/70 px-2 py-1.5"
            data-testid="dossier-doc-row"
          >
            <span class="min-w-0 text-xs text-slate-700">
              <span class="font-medium">{{ docTitle(row) }}</span>
              <span v-if="row.doc_number" class="text-slate-500"> · {{ row.doc_number }}</span>
              <span class="text-slate-500"> · {{ stateLabel(row.workflow_state) }}</span>
            </span>

            <!-- CÓ tệp ⇒ mở được thật -->
            <a
              v-if="fileState(row) === 'yes'"
              :href="row.file_url"
              target="_blank"
              rel="noopener noreferrer"
              :aria-label="`Mở tệp của hồ sơ ${docTitle(row)}`"
              :title="row.is_private === 1
                ? 'Tệp riêng tư — cần đăng nhập hệ thống để mở.'
                : 'Mở tệp đính kèm trong tab mới.'"
              class="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:underline rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              data-testid="dossier-file-open"
            >
              <span>Mở tệp</span>
              <span class="text-slate-500 font-normal" data-testid="dossier-file-name">
                ({{ fileMeta(row) }})
              </span>
            </a>

            <!-- KHÔNG có tệp ⇒ nói thẳng + nút vô hiệu hoá (không giả vờ bấm được) -->
            <button
              v-else-if="fileState(row) === 'no'"
              type="button"
              disabled
              aria-disabled="true"
              title="Hồ sơ này chưa có tệp đính kèm. Hãy tải tệp lên ở màn Hồ sơ thiết bị."
              class="text-xs text-slate-400 cursor-not-allowed rounded border border-dashed border-slate-300 px-2 py-0.5"
              data-testid="dossier-file-none"
            >
              Chưa đính kèm tệp
            </button>

            <!-- Server chưa cấp thông tin tệp ⇒ nói "chưa biết", KHÔNG kết luận sai -->
            <span
              v-else
              class="text-xs text-slate-400"
              title="Máy chủ chưa cung cấp thông tin tệp cho hồ sơ này."
              data-testid="dossier-file-unknown"
            >
              Chưa có thông tin tệp
            </span>
          </li>
        </ul>
      </div>
    </div>

    <p v-if="hiddenCount > 0" class="mt-2 text-xs text-slate-500" data-testid="dossier-hidden">
      ({{ hiddenCount }} tài liệu bị ẩn theo phân quyền)
    </p>

    <div class="mt-3 flex items-center justify-between gap-3">
      <p
        v-if="!compliant"
        class="text-xs text-red-700 font-medium"
        data-testid="dossier-block-warning"
      >
        Cần hoàn thiện hồ sơ trước khi trình duyệt phiếu.
      </p>
      <button
        type="button"
        class="text-xs text-brand-600 hover:underline ml-auto rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
        aria-label="Làm mới trạng thái hồ sơ pháp lý"
        data-testid="dossier-refresh"
        @click="emit('refresh')"
      >
        Làm mới
      </button>
    </div>
  </div>
</template>
