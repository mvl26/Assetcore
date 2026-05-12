<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Chi tiết Kiểm toán nội bộ — Start / Complete checklist / Close.
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import { useApi } from '@/composables/useApi'
import { getAudit } from '@/api/imm16'
import type { InternalAudit, ChecklistItemPayload } from '@/api/imm16'
import { formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store = useImm16Store()
const api = useApi()

const audit = ref<InternalAudit | null>(null)
const loading = ref(false)
const activeTab = ref<'overview' | 'checklist' | 'report'>('overview')

async function load() {
  loading.value = true
  try { audit.value = await getAudit(props.id) }
  finally { loading.value = false }
}

const canStart = computed(() => audit.value?.status === 'Planned')
const canChecklist = computed(() => audit.value?.status === 'In Progress')
const canClose = computed(() => audit.value && ['In Progress', 'Reporting'].includes(audit.value.status))

async function doStart() {
  if (!audit.value) return
  const res = await api.run(() => store.actionStartAudit(audit.value!.name), {
    successMessage: 'Đã bắt đầu kiểm toán',
  })
  if (res) await load()
}

// Checklist items — local editor
const checklistItems = ref<ChecklistItemPayload[]>([
  { idx: 1, finding_status: 'Compliant', notes: '', clause_ref: '' },
])
function addChecklistRow() {
  checklistItems.value.push({ idx: checklistItems.value.length + 1, finding_status: 'Compliant', notes: '', clause_ref: '' })
}
function removeChecklistRow(i: number) {
  checklistItems.value.splice(i, 1)
  checklistItems.value.forEach((it, idx) => (it.idx = idx + 1))
}

async function submitChecklist() {
  if (!audit.value) return
  const res = await api.run(() => store.actionCompleteChecklist(audit.value!.name, checklistItems.value), {
    successMessage: 'Đã lưu bảng kiểm + sinh findings',
  })
  if (res) await load()
}

// Close
const showClose = ref(false)
const reportSummary = ref('')
async function doClose() {
  if (!audit.value) return
  const res = await api.run(() => store.actionCloseAudit(audit.value!.name, reportSummary.value), {
    successMessage: 'Đã đóng kiểm toán',
  })
  if (res) { showClose.value = false; reportSummary.value = ''; await load() }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <div v-if="loading" class="p-6"><SkeletonLoader variant="form" :rows="6" /></div>

    <template v-else-if="audit">
      <PageHeader
        :title="audit.audit_code"
        :subtitle="`${audit.audit_type} · ${formatDate(audit.planned_start)} → ${formatDate(audit.planned_end)}`"
        :breadcrumb="[
          { label: 'IMM-16 · Tuân thủ' },
          { label: 'Kiểm toán', to: '/compliance/audits' },
          { label: audit.audit_code },
        ]"
      >
        <template #actions>
          <button class="btn-ghost text-sm" @click="router.push('/compliance/audits')">Quay lại</button>
          <button v-if="canStart" class="btn-primary text-sm" @click="doStart">Bắt đầu</button>
          <button v-if="canClose" class="btn-ghost text-sm" @click="showClose = true">Đóng kiểm toán</button>
        </template>
      </PageHeader>

      <!-- Summary card -->
      <div class="card p-5">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="text-xs text-slate-400 mb-1">Trạng thái</p>
            <StatusBadge :state="audit.status" />
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Trưởng đoàn</p>
            <p class="text-sm text-slate-700">{{ audit.lead_auditor || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Bắt đầu thực tế</p>
            <p class="text-sm text-slate-700">{{ formatDate(audit.actual_start) }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-400 mb-1">Kết thúc thực tế</p>
            <p class="text-sm text-slate-700">{{ formatDate(audit.actual_end) }}</p>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b border-slate-200">
        <nav class="-mb-px flex gap-6">
          <button :class="['py-2 px-1 border-b-2 text-sm font-medium transition-colors',
            activeTab === 'overview' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = 'overview'">
            Tổng quan
          </button>
          <button :class="['py-2 px-1 border-b-2 text-sm font-medium transition-colors',
            activeTab === 'checklist' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = 'checklist'">
            Bảng kiểm
          </button>
          <button :class="['py-2 px-1 border-b-2 text-sm font-medium transition-colors',
            activeTab === 'report' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-500 hover:text-slate-700']"
            @click="activeTab = 'report'">
            Báo cáo & Phát hiện
          </button>
        </nav>
      </div>

      <!-- Tab content -->
      <div v-if="activeTab === 'overview'" class="card p-5">
        <p class="text-sm text-slate-600">
          Tổng số phát hiện trong đợt kiểm toán: <strong>{{ audit.findings_count }}</strong>
        </p>
        <button class="mt-3 text-sm text-blue-600 hover:underline"
                @click="router.push({ path: '/compliance/findings', query: { audit: audit.name } })">
          Xem các phát hiện liên quan →
        </button>
      </div>

      <div v-else-if="activeTab === 'checklist'" class="card p-5">
        <div v-if="!canChecklist" class="text-sm text-slate-500 py-6 text-center">
          Bảng kiểm chỉ chỉnh sửa được khi kiểm toán đang "In Progress".
          <span v-if="audit.status === 'Planned'">— Hãy nhấn "Bắt đầu" trước.</span>
        </div>
        <template v-else>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-slate-100">
              <thead>
                <tr>
                  <th class="table-header w-12">#</th>
                  <th class="table-header">Tham chiếu điều khoản</th>
                  <th class="table-header">Kết quả</th>
                  <th class="table-header">Ghi chú</th>
                  <th class="table-header w-16"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="(item, i) in checklistItems" :key="i">
                  <td class="table-cell font-mono text-xs text-slate-500">{{ item.idx }}</td>
                  <td class="table-cell">
                    <input v-model="item.clause_ref" class="form-input text-sm" placeholder="ISO 13485 §7.5.6" />
                  </td>
                  <td class="table-cell">
                    <select v-model="item.finding_status" class="form-select text-sm">
                      <option value="Compliant">Compliant</option>
                      <option value="Minor NC">Minor NC</option>
                      <option value="Major NC">Major NC</option>
                      <option value="N/A">N/A</option>
                    </select>
                  </td>
                  <td class="table-cell">
                    <input v-model="item.notes" class="form-input text-sm" />
                  </td>
                  <td class="table-cell text-right">
                    <button class="text-xs text-red-600 hover:text-red-800"
                            :disabled="checklistItems.length === 1"
                            @click="removeChecklistRow(i)">Xóa</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="flex justify-between mt-3">
            <button class="btn-ghost text-sm" @click="addChecklistRow">+ Thêm dòng</button>
            <button class="btn-primary text-sm" :disabled="api.loading.value" @click="submitChecklist">
              Hoàn tất bảng kiểm
            </button>
          </div>
        </template>
      </div>

      <div v-else-if="activeTab === 'report'" class="card p-5">
        <p class="text-sm text-slate-600 mb-3">Danh sách phát hiện sinh từ đợt kiểm toán này.</p>
        <button class="btn-ghost text-sm"
                @click="router.push({ path: '/compliance/findings', query: { audit: audit.name } })">
          Mở danh sách phát hiện →
        </button>
      </div>
    </template>

    <BaseModal v-if="showClose" title="Đóng đợt kiểm toán" size="md" @close="showClose = false">
      <div class="form-group">
        <label class="form-label">Tóm tắt báo cáo</label>
        <textarea v-model="reportSummary" rows="5" class="form-input" />
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showClose = false">Hủy</button>
        <button class="btn-primary" :disabled="api.loading.value" @click="doClose">Đóng kiểm toán</button>
      </template>
    </BaseModal>
  </div>
</template>
