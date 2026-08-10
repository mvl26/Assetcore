<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Chi tiết Quy tắc tuân thủ (BUG-16-02): xem toàn bộ field + version history,
// Sửa, Ngừng/Kích hoạt, Tạo phiên bản mới (change-control QMS — CLAUDE.md §12).
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import type { ComplianceRule } from '@/api/imm16'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import RecordHistory from '@/components/common/RecordHistory.vue'
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'
import { translateFrequency } from '@/utils/formatters'

const route = useRoute()
const router = useRouter()
const store = useImm16Store()
const api = useApi()
const name = route.params.id as string

const rule = ref<ComplianceRule | null>(null)
const loading = ref(true)
// Lỗi của LƯỢT NẠP — ref RIÊNG, giữ NGUYÊN đối tượng lỗi để `useDetailAccess` phân loại
// được kind (mạng / 403-in-envelope / 404). KHÔNG dùng chung với lỗi hành động.
const loadError = ref<unknown>(null)
const { kind: loadKind, message: loadMsg } = useDetailAccess(() => loadError.value)
const historyRef = ref<InstanceType<typeof RecordHistory> | null>(null)

const CATEGORIES = ['Document', 'PM', 'Calibration', 'Training', 'Stock', 'SLA', 'Safety']
// Khớp BE ground truth (imm_compliance_rule.evaluation_frequency).
const FREQS = ['Realtime', 'Hourly', 'Daily', 'Weekly', 'Monthly', 'Quarterly']

// Mã quy tắc sai / đã xoá ⇒ 404: KHÔNG để ApiError nổi lên console và KHÔNG dừng
// ở dòng chữ đỏ cụt — render empty-state chuẩn kèm lối về danh sách quy tắc.
async function load() {
  loadError.value = null // INV-UX4-7 — xoá lỗi ở DÒNG ĐẦU, nếu không nút «Thử lại» trông như chết
  loading.value = true
  try {
    rule.value = await store.fetchRule(name)
  } catch (e: unknown) {
    loadError.value = e
    rule.value = null
  } finally {
    loading.value = false
  }
}
function refreshAll() {
  load()
  historyRef.value?.reload()
}

// ── Edit (non-versioned fields) ──
const showEdit = ref(false)
const editForm = ref<Partial<ComplianceRule>>({})
function openEdit() {
  if (!rule.value) return
  editForm.value = {
    rule_name: rule.value.rule_name,
    category: rule.value.category,
    evaluation_frequency: rule.value.evaluation_frequency,
    regulatory_reference: rule.value.regulatory_reference,
    qms_doc_ref: rule.value.qms_doc_ref,
  }
  showEdit.value = true
}
async function saveEdit() {
  const res = await api.run(
    () => store.actionUpdateRule(name, editForm.value, ''),
    { successMessage: 'Đã lưu thay đổi quy tắc' },
  )
  if (res) { showEdit.value = false; refreshAll() }
}

// ── New version (threshold/severity change → bump version, requires summary) ──
const showVersion = ref(false)
const versionForm = ref<{ threshold_definition: string; severity: ComplianceRule['severity']; change_summary: string }>({
  threshold_definition: '', severity: 'Medium', change_summary: '',
})
function openVersion() {
  if (!rule.value) return
  versionForm.value = {
    threshold_definition: rule.value.threshold_definition || '',
    severity: rule.value.severity,
    change_summary: '',
  }
  showVersion.value = true
}
async function saveVersion() {
  if (!versionForm.value.change_summary.trim()) {
    api.run(() => Promise.reject(new Error('Phải nhập tóm tắt thay đổi (VR-11)')), {})
    return
  }
  const res = await api.run(
    () => store.actionUpdateRule(
      name,
      {
        threshold_definition: versionForm.value.threshold_definition,
        severity: versionForm.value.severity,
      },
      versionForm.value.change_summary,
    ),
    { successMessage: 'Đã tạo phiên bản mới của quy tắc' },
  )
  if (res) { showVersion.value = false; refreshAll() }
}

async function toggleActive() {
  if (!rule.value) return
  const wasActive = rule.value.is_active
  const fn = wasActive
    ? () => store.actionDeactivateRule(name).then(() => true)
    : () => store.actionReactivateRule(name).then(() => true)
  const res = await api.run(fn, {
    successMessage: wasActive ? 'Đã ngừng áp dụng' : 'Đã kích hoạt lại',
  })
  if (res) refreshAll()
}

function fmtDate(d?: string) {
  return d ? new Date(d).toLocaleDateString('vi-VN') : '—'
}
const fields = computed(() => {
  const r = rule.value
  if (!r) return []
  return [
    ['Mã quy tắc', r.rule_code],
    ['Module nguồn', r.source_module],
    ['Nhóm', r.category],
    ['Tần suất đánh giá', translateFrequency(r.evaluation_frequency)],
    ['Nguồn dữ liệu', `${r.data_source_doctype || '—'}${r.data_source_field ? ' · ' + r.data_source_field : ''}`],
    ['Vai trò sở hữu', r.owner_role || '—'],
    ['Tham chiếu hệ thống quản lý chất lượng', r.qms_doc_ref || '—'],
    ['Tham chiếu pháp lý', r.regulatory_reference || '—'],
    ['Ngày hiệu lực', fmtDate(r.effective_date)],
  ] as [string, string | undefined][]
})

onMounted(load)
</script>

<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadKind"
    :error-message="loadMsg"
    :doc="rule"
    entity-label="quy tắc tuân thủ"
    :record-id="name"
    back-label="Về danh sách quy tắc"
    @retry="load()"
    @back="router.push('/compliance/rules')">
    <!-- Vùng DUY NHẤT hiện ở mọi trạng thái ⇒ luôn biết đang ở màn nào, kể cả khi 404. -->
    <template #title>
      <PageHeader
        :title="rule?.rule_name || 'Chi tiết quy tắc tuân thủ'"
        :subtitle="`IMM-16 · Quy tắc tuân thủ — ${rule?.rule_code || name}`"
        :breadcrumb="[
          { label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' },
          { label: 'Quy tắc', to: '/compliance/rules' },
          { label: rule?.rule_code || name },
        ]"
      />
    </template>

    <!-- CHỈ render ở trạng thái content ⇒ 0 nút chết khi bản ghi không đọc được. -->
    <template #actions>
      <button class="btn-secondary text-sm" data-testid="cta-edit" @click="openEdit">Sửa</button>
      <button class="btn-primary text-sm" data-testid="cta-new-version" @click="openVersion">
        Tạo phiên bản mới
      </button>
      <button
        v-if="rule"
        class="text-sm font-medium px-3 py-1.5 rounded-lg border"
        data-testid="cta-toggle-active"
        :class="rule.is_active ? 'text-red-600 border-red-200 hover:bg-red-50' : 'text-emerald-700 border-emerald-200 hover:bg-emerald-50'"
        @click="toggleActive"
      >{{ rule.is_active ? 'Ngừng áp dụng' : 'Kích hoạt lại' }}</button>
    </template>

    <template v-if="rule">
      <div class="card p-5 space-y-4">
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :state="rule.severity" />
          <span
            :class="rule.is_active ? 'text-emerald-700 bg-emerald-50 border-emerald-100' : 'text-slate-600 bg-slate-50 border-slate-200'"
            class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium border"
          >{{ rule.is_active ? 'Đang áp dụng' : 'Ngừng áp dụng' }}</span>
          <span class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-100">
            v{{ rule.version || '1.0' }}
          </span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
          <div v-for="[label, val] in fields" :key="label">
            <p class="t-eyebrow mb-1">{{ label }}</p>
            <p class="text-slate-700">{{ val || '—' }}</p>
          </div>
        </div>
        <div class="pt-3 border-t border-slate-100">
          <p class="t-eyebrow mb-1">Định nghĩa ngưỡng (threshold_definition)</p>
          <pre class="text-xs bg-slate-50 rounded p-3 overflow-x-auto text-slate-700">{{ rule.threshold_definition || '—' }}</pre>
        </div>
      </div>

      <!-- Version / change control -->
      <div class="card p-5">
        <h2 class="font-semibold text-slate-700 mb-3">Kiểm soát phiên bản</h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <div><p class="t-eyebrow mb-1">Phiên bản hiện tại</p><p class="font-mono text-slate-700">v{{ rule.version || '1.0' }}</p></div>
          <div><p class="t-eyebrow mb-1">Phiên bản trước</p><p class="font-mono text-slate-700">{{ rule.previous_version ? 'v' + rule.previous_version : '—' }}</p></div>
          <div><p class="t-eyebrow mb-1">Tóm tắt thay đổi gần nhất</p><p class="text-slate-700">{{ rule.change_summary || '—' }}</p></div>
        </div>
      </div>

      <RecordHistory ref="historyRef" ref-doctype="IMM Compliance Rule" :ref-name="rule.name" />
    </template>

    <!-- Edit modal — nằm TRONG nhánh content: hộp thoại chỉ mở được từ CTA, mà CTA
         không tồn tại ngoài trạng thái có-dữ-liệu. -->
    <BaseModal v-if="showEdit" title="Sửa quy tắc" size="lg" @close="showEdit = false">
      <div class="space-y-3">
        <div class="form-group">
          <label class="form-label">Tên quy tắc</label>
          <input v-model="editForm.rule_name" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Nhóm</label>
          <select v-model="editForm.category" class="form-select">
            <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Tần suất đánh giá</label>
          <select v-model="editForm.evaluation_frequency" class="form-select">
            <option v-for="f in FREQS" :key="f" :value="f">{{ translateFrequency(f) }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Tham chiếu pháp lý</label>
          <input v-model="editForm.regulatory_reference" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">Tham chiếu hệ thống quản lý chất lượng</label>
          <input v-model="editForm.qms_doc_ref" class="form-input" />
        </div>
        <p class="text-xs text-slate-400">Đổi ngưỡng/mức độ → dùng "Tạo phiên bản mới" để kiểm soát thay đổi (VR-11).</p>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showEdit = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="saveEdit">Lưu</button>
      </template>
    </BaseModal>

    <!-- New version modal -->
    <BaseModal v-if="showVersion" title="Tạo phiên bản mới (kiểm soát thay đổi)" size="lg" @close="showVersion = false">
      <div class="space-y-3">
        <p class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
          VR-11: thay đổi ngưỡng hoặc mức độ sẽ tăng số phiên bản và yêu cầu tóm tắt thay đổi.
        </p>
        <div class="form-group">
          <label class="form-label">Mức độ</label>
          <select v-model="versionForm.severity" class="form-select">
            <option value="Low">Thấp</option>
            <option value="Medium">Trung bình</option>
            <option value="High">Cao</option>
            <option value="Critical">Nghiêm trọng</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Định nghĩa ngưỡng (JSON)</label>
          <textarea v-model="versionForm.threshold_definition" rows="4" class="form-input font-mono text-xs" />
        </div>
        <div class="form-group">
          <label class="form-label">Tóm tắt thay đổi *</label>
          <textarea v-model="versionForm.change_summary" rows="3" class="form-input" placeholder="Lý do & nội dung thay đổi..." />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showVersion = false">Huỷ</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="saveVersion">Tạo phiên bản</button>
      </template>
    </BaseModal>
  </DetailPageShell>
</template>
