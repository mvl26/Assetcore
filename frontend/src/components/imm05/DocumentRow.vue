<template>
  <tr :class="rowClass">
    <!-- Mã tài liệu -->
    <td>
      <RouterLink :to="`/documents/view/${doc.name}`" class="doc-link">
        {{ doc.name }}
      </RouterLink>
    </td>

    <!-- Thiết bị -->
    <td>
      <div class="font-medium text-gray-900 truncate max-w-[220px]">
        {{ formatAssetDisplay(doc.asset_name, doc.asset_ref).main }}
      </div>
      <div v-if="formatAssetDisplay(doc.asset_name, doc.asset_ref).hasBoth"
           class="text-xs text-gray-500 font-mono">
        {{ formatAssetDisplay(doc.asset_name, doc.asset_ref).sub }}
      </div>
    </td>

    <!-- Nhóm -->
    <td>
      <span class="badge" :class="`badge-${(doc.doc_category || 'general').toLowerCase()}`">
        {{ doc.doc_category || '—' }}
      </span>
    </td>

    <!-- Loại tài liệu -->
    <td>
      {{ doc.doc_type_detail }}
      <span v-if="doc.is_exempt" class="exempt-tag" title="Miễn đăng ký NĐ98">Miễn đăng ký</span>
    </td>

    <!-- Phiên bản -->
    <td>{{ doc.version }}</td>

    <!-- Trạng thái -->
    <td>
      <span class="state-badge" :class="`state-${(doc.workflow_state || 'draft').toLowerCase()}`">
        {{ stateLabel(doc.workflow_state || '') }}
      </span>
      <span
        v-if="showExemptBadge"
        class="exempt-miễn-badge"
        title="Miễn đăng ký NĐ98"
      >Miễn</span>
    </td>

    <!-- Hết hạn -->
    <td :class="expiryClass">
      <template v-if="!doc.expiry_date">—</template>
      <template v-else>
        {{ formatDate(doc.expiry_date) }}
        <span v-if="expiryInfo.label" class="expiry-tag">{{ expiryInfo.label }}</span>
      </template>
    </td>

    <!-- Hành động -->
    <td class="actions">
      <!-- Approve / Reject chỉ khi Pending_Review -->
      <button
        v-if="doc.workflow_state === 'Pending_Review'"
        class="btn btn-xs btn-success"
        @click="$emit('approve', doc.name)"
      >Duyệt</button>

      <button
        v-if="doc.workflow_state === 'Pending_Review'"
        class="btn btn-xs btn-danger"
        @click="$emit('reject', doc.name)"
      >Từ chối</button>

      <!-- Yêu cầu bổ sung -->
      <button
        v-if="doc.workflow_state !== 'Active'"
        class="btn btn-xs btn-outline"
        @click="$emit('request-doc', doc)"
        title="Tạo yêu cầu bổ sung tài liệu"
      >+ Yêu cầu</button>

      <!-- Đánh dấu Exempt (chỉ Legal chưa Active) -->
      <button
        v-if="doc.doc_category === 'Legal' && doc.workflow_state !== 'Active' && !doc.is_exempt"
        class="btn btn-xs btn-warning"
        @click="$emit('exempt', doc)"
        title="Đánh dấu miễn đăng ký NĐ98"
      >Miễn đăng ký</button>

      <!-- Lịch sử -->
      <button
        class="btn btn-xs btn-ghost"
        @click="$emit('history', doc.name)"
        title="Xem lịch sử thay đổi"
      >Log</button>
    </td>
  </tr>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AssetDocumentItem } from '@/api/imm05'
import { stateLabel, formatDate } from '@/utils/docUtils'
import { formatAssetDisplay } from '@/utils/formatters'

const props = defineProps<{ doc: AssetDocumentItem }>()

defineEmits<{
  approve: [name: string]
  reject: [name: string]
  'request-doc': [doc: AssetDocumentItem]
  exempt: [doc: AssetDocumentItem]
  history: [name: string]
}>()

// computed() để reactive khi store mutate doc.workflow_state in-place sau Approve/Reject
const rowClass = computed(() => {
  if (props.doc.is_exempt) return ''
  const s = props.doc.workflow_state
  if (s === 'Pending_Review') return 'row-pending'
  if (s === 'Expired') return 'row-expired'
  if (s === 'Rejected') return 'row-rejected'
  return ''
})

// ── Expiry highlighting logic (Task 1a) ───────────────────────────────────────
interface ExpiryInfo {
  cssClass: string
  label: string | null
  daysLeft: number | null
}

const expiryInfo = computed<ExpiryInfo>(() => {
  const raw = props.doc.expiry_date
  if (!raw) return { cssClass: '', label: null, daysLeft: null }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const expiry = new Date(raw)
  expiry.setHours(0, 0, 0, 0)
  const diffMs = expiry.getTime() - today.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays <= 0) {
    return { cssClass: 'text-red-600 font-semibold', label: 'Hết hạn', daysLeft: diffDays }
  }
  if (diffDays <= 30) {
    return { cssClass: 'text-orange-600 font-semibold', label: `${diffDays} ngày`, daysLeft: diffDays }
  }
  if (diffDays <= 90) {
    return { cssClass: 'text-yellow-600', label: null, daysLeft: diffDays }
  }
  return { cssClass: '', label: null, daysLeft: diffDays }
})

const expiryClass = computed(() => expiryInfo.value.cssClass)

// ── Exempt badge check (Task 1b) ──────────────────────────────────────────────
const showExemptBadge = computed(() =>
  props.doc.is_exempt === 1
)

</script>

<style scoped>
.doc-link { color: #4f8ef7; text-decoration: none; }
.doc-link:hover { text-decoration: underline; }

.exempt-tag {
  display: inline-block; margin-left: 4px;
  font-size: 0.65rem; padding: 1px 5px;
  background: #fef3c7; color: #92400e;
  border-radius: 10px; font-weight: 600;
}

.badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
.badge-legal { background: #dbeafe; color: #1e40af; }
.badge-technical { background: #d1fae5; color: #065f46; }
.badge-certification { background: #ede9fe; color: #5b21b6; }
.badge-training { background: #fce7f3; color: #9d174d; }
.badge-qa { background: #fef3c7; color: #92400e; }

.state-badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
.state-active { background: #d1fae5; color: #065f46; }
.state-draft { background: #e5e7eb; color: #374151; }
.state-pending_review { background: #fef3c7; color: #92400e; }
.state-expired { background: #fee2e2; color: #991b1b; }
.state-archived { background: #e5e7eb; color: #374151; }
.state-rejected { background: #fce7f3; color: #831843; }

.expiry-days { color: inherit; opacity: 0.75; }

.exempt-miễn-badge {
  display: inline-block; margin-left: 4px;
  font-size: 0.65rem; padding: 1px 5px;
  background: #ccfbf1; color: #0f766e;
  border-radius: 10px; font-weight: 600;
}

.expiry-tag {
  display: inline-block; margin-left: 4px;
  font-size: 0.7rem; padding: 0 5px;
  background: rgba(0,0,0,0.07); border-radius: 8px;
  vertical-align: middle;
}

.actions { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.btn { padding: 0.45rem 1rem; border-radius: 4px; border: none; cursor: pointer; font-size: 0.875rem; }
.btn-xs { padding: 0.2rem 0.5rem; font-size: 0.75rem; }
.btn-success { background: #166534; color: #ffffff; }
.btn-danger { background: #dc2626; color: #ffffff; }
.btn-outline { background: transparent; border: 1px solid #d1d5db; color: #374151; }
.btn-warning { background: #78350f; color: #ffffff; }
.btn-ghost { background: transparent; color: #6b7280; border: 1px solid #e5e7eb; }
.btn-ghost:hover { background: #f9fafb; }

.text-danger { color: #ef4444; }
.text-warning { color: #f59e0b; }
</style>
