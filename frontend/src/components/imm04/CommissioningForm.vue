<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import WorkflowActions from '@/components/imm04/WorkflowActions.vue'
import BaselineTestTable from '@/components/imm04/BaselineTestTable.vue'
import DocumentChecklist from '@/components/imm04/DocumentChecklist.vue'
import QRLabel from '@/components/imm04/QRLabel.vue'
import { useCommissioningStore } from '@/stores/commissioning'
import type { CommissioningDoc, WorkflowState, DocumentRecord, BaselineTest } from '@/types/imm04'
import { formatDatetime } from '@/utils/docUtils'

const props = defineProps<{
  doc: CommissioningDoc
  // IMM-05 compliance props (optional — graceful khi IMM-05 chưa deploy)
  imm05DocStatus?: string | null
  imm05Pct?: number
  imm05Missing?: string[]
  imm05IsCompliant?: boolean
}>()

const emit = defineEmits<{
  (e: 'transition', action: string): void
  (e: 'submit'): void
  (e: 'saved'): void
  (e: 'refresh-imm05'): void
}>()

const store = useCommissioningStore()

// ─── Local edits tracking ───────────────────────────────────────────────────

const pendingChanges = reactive<Record<string, unknown>>({})
const hasPendingChanges = computed(() => Object.keys(pendingChanges).length > 0)
const saving = ref(false)
const saveMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null)

function trackChange(field: string, value: unknown) {
  pendingChanges[field] = value
}

async function handleSave() {
  if (!hasPendingChanges.value) return
  saving.value = true
  saveMessage.value = null

  const ok = await store.saveDoc(props.doc.name, { ...pendingChanges })
  if (ok) {
    // Clear pending
    Object.keys(pendingChanges).forEach((k) => delete pendingChanges[k])
    saveMessage.value = { type: 'success', text: 'Đã lưu thành công' }
    emit('saved')
  } else {
    saveMessage.value = { type: 'error', text: store.error ?? 'Lỗi khi lưu' }
  }
  saving.value = false
  setTimeout(() => { saveMessage.value = null }, 4000)
}

// ─── Document checklist updates ─────────────────────────────────────────────

function onDocUpdate(idx: number, field: keyof DocumentRecord, value: string) {
  const docs = props.doc.commissioning_documents.map((d) => {
    if (d.idx === idx) {
      return { idx: d.idx, [field]: value }
    }
    return null
  }).filter(Boolean)

  // Merge into pending
  const existing = (pendingChanges.commissioning_documents as Record<string, unknown>[] | undefined) ?? []
  const merged = [...existing.filter((r: Record<string, unknown>) => r.idx !== idx), ...docs]
  pendingChanges.commissioning_documents = merged
}

// ─── Baseline test updates ──────────────────────────────────────────────────

function onTestUpdate(idx: number, field: keyof BaselineTest, value: string | number) {
  const existing = (pendingChanges.baseline_tests as Record<string, unknown>[] | undefined) ?? []
  const row = existing.find((r: Record<string, unknown>) => r.idx === idx) ?? { idx }
  ;(row as Record<string, unknown>)[field] = value
  pendingChanges.baseline_tests = [...existing.filter((r: Record<string, unknown>) => r.idx !== idx), row]
}

// ─── File upload ─────────────────────────────────────────────────────────────

const uploading = ref(false)

async function handleFileUpload(event: Event, fieldName: string) {
  const input = event.target as HTMLInputElement
  const file = input?.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('doctype', 'Asset Commissioning')
    formData.append('docname', props.doc.name)
    formData.append('fieldname', fieldName)
    formData.append('is_private', '1')

    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      body: formData,
      credentials: 'include',
    })
    const data = await res.json()
    if (data.message?.file_url) {
      trackChange(fieldName, data.message.file_url)
      saveMessage.value = { type: 'success', text: `File "${file.name}" đã upload. Nhấn Lưu để hoàn tất.` }
    }
  } catch {
    saveMessage.value = { type: 'error', text: 'Lỗi upload file' }
  } finally {
    uploading.value = false
  }
}

// ─── Tabs ────────────────────────────────────────────────────────────────────

type TabId = 'general' | 'documents' | 'safety' | 'output'

interface Tab {
  id: TabId
  label: string
  visibleStates: WorkflowState[] | 'all'
}

const TABS: Tab[] = [
  { id: 'general', label: 'Thông tin chung', visibleStates: 'all' },
  {
    id: 'documents',
    label: 'Hồ sơ đi kèm',
    visibleStates: ['Draft', 'Identification', 'Installing', 'Initial_Inspection', 'Clinical_Hold', 'Re_Inspection', 'Pending_Release', 'Clinical_Release'],
  },
  {
    id: 'safety',
    label: 'Kiểm tra an toàn',
    visibleStates: ['Installing', 'Initial_Inspection', 'Clinical_Hold', 'Re_Inspection', 'Pending_Release', 'Clinical_Release'],
  },
  {
    id: 'output',
    label: 'Kết quả triển khai',
    visibleStates: ['Pending_Release', 'Clinical_Release'],
  },
]

const activeTab = ref<TabId>('general')

const visibleTabs = computed(() => {
  return TABS.filter((tab) => {
    if (tab.visibleStates === 'all') return true
    return tab.visibleStates.includes(props.doc.workflow_state)
  })
})

watch(
  () => props.doc.workflow_state,
  () => {
    const visible = visibleTabs.value.map((t) => t.id)
    if (!visible.includes(activeTab.value)) {
      activeTab.value = 'general'
    }
  },
)

// ─── Computed ────────────────────────────────────────────────────────────────

const isReadonly = computed(() => props.doc.is_locked)
const hasAsset = computed(() => Boolean(props.doc.final_asset))

const showRadiationWarning = computed(
  () =>
    props.doc.is_radiation_device &&
    !['Clinical_Release', 'Return_To_Vendor'].includes(props.doc.workflow_state),
)

const showDOAAlert = computed(() => props.doc.doa_incident)

const isHighRisk = computed(() =>
  ['C', 'D', 'Radiation'].includes(props.doc?.risk_class ?? '') ||
  props.doc?.is_radiation_device === 1
)

const showBoardApprover = computed(() =>
  ['Initial_Inspection', 'Clinical_Hold', 'Re_Inspection', 'Clinical_Release', 'Pending_Release']
    .includes(props.doc?.workflow_state ?? '')
)

const showOverallInspectionResult = computed(() => {
  if (props.doc?.overall_inspection_result) return true
  return ['Initial_Inspection', 'Re_Inspection', 'Clinical_Hold', 'Clinical_Release', 'Pending_Release']
    .includes(props.doc?.workflow_state ?? '')
})

const showQaOfficer = computed(() => isHighRisk.value)
</script>

<template>
  <div class="space-y-6">
    <!-- Header bar: name + state + actions -->
    <div class="card">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="flex items-center gap-3 mb-1">
            <h2 class="text-xl font-bold text-gray-900 font-mono">{{ doc.name }}</h2>
            <StatusBadge :state="doc.workflow_state" size="md" />
            <span
              v-if="doc.docstatus === 1"
              class="inline-flex items-center gap-1 text-xs bg-emerald-100 text-emerald-800 px-2 py-1 rounded-full font-medium"
            >
              Submitted
            </span>
          </div>
          <p class="text-sm text-gray-500">
            Cập nhật: {{ formatDatetime(doc.modified) }}
            <span class="mx-1">&middot;</span>
            Bởi: {{ doc.owner }}
          </p>
        </div>

        <div class="flex items-center gap-3">
          <!-- Save button -->
          <button
            v-if="!isReadonly && hasPendingChanges"
            class="btn-primary px-4 py-2 text-sm"
            :disabled="saving"
            @click="handleSave"
          >
            <svg v-if="saving" class="w-4 h-4 animate-spin mr-1" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {{ saving ? 'Đang lưu...' : 'Lưu thay đổi' }}
          </button>

          <!-- Workflow actions -->
          <WorkflowActions
            :current-state="doc.workflow_state"
            :allowed-transitions="doc.allowed_transitions"
            :is-locked="doc.is_locked"
            :can-submit="store.canSubmitDoc"
            :loading="store.loading"
            :imm05-is-compliant="imm05IsCompliant ?? true"
            @transition="emit('transition', $event)"
            @submit="emit('submit')"
          />
        </div>
      </div>

      <!-- Save toast -->
      <Transition name="fade">
        <div
          v-if="saveMessage"
          class="mt-3 p-3 rounded-lg text-sm flex items-center gap-2"
          :class="saveMessage.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'"
        >
          <svg v-if="saveMessage.type === 'success'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01" />
          </svg>
          {{ saveMessage.text }}
        </div>
      </Transition>
    </div>

    <!-- Alerts -->
    <div v-if="showRadiationWarning" class="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
      <svg class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div>
        <p class="text-sm font-semibold text-yellow-800">Thiết bị phát bức xạ / tia X</p>
        <p class="text-xs text-yellow-700 mt-0.5">Bắt buộc upload Giấy phép Cục An toàn Bức xạ trước khi Phát hành.</p>
      </div>
    </div>

    <div v-if="showDOAAlert" class="flex items-start gap-3 p-4 bg-red-50 border border-red-300 rounded-lg">
      <svg class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <p class="text-sm font-semibold text-red-800">Sự cố DOA đã được báo cáo</p>
        <p class="text-xs text-red-700 mt-0.5">Thiết bị này đã có Phiếu NC DOA. Vui lòng xử lý trước khi tiếp tục.</p>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="border-b border-gray-200">
      <nav class="-mb-px flex gap-6 overflow-x-auto" aria-label="Tabs">
        <button
          v-for="tab in visibleTabs"
          :key="tab.id"
          :class="[
            'whitespace-nowrap pb-3 px-1 text-sm font-medium border-b-2 transition-colors',
            activeTab === tab.id
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- Tab Content -->

    <!-- Tab: Thông tin chung -->
    <div v-show="activeTab === 'general'" class="card space-y-6">
      <h3 class="text-base font-semibold text-gray-900 pb-2 border-b">Thông tin Mua sắm & Lắp đặt</h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label class="form-label">Lệnh mua hàng (PO)</label>
          <input type="text" :value="doc.po_reference" class="form-input" readonly />
        </div>
        <div>
          <label class="form-label">Model Thiết bị</label>
          <input type="text" :value="doc.master_item" class="form-input" readonly />
        </div>
        <div>
          <label class="form-label">Nhà cung cấp</label>
          <input type="text" :value="doc.vendor" class="form-input" readonly />
        </div>
        <div>
          <label class="form-label">Khoa / Phòng nhận</label>
          <input type="text" :value="doc.clinical_dept" class="form-input" readonly />
        </div>
        <div>
          <label class="form-label">Trưởng khoa</label>
          <input
            type="text"
            :value="doc.clinical_head || ''"
            @change="trackChange('clinical_head', ($event.target as HTMLInputElement).value)"
            :disabled="isReadonly"
            placeholder="User ID trưởng khoa"
            class="form-input"
          />
          <small class="form-hint">Nhập User ID (vd: user@hospital.com)</small>
        </div>
        <div>
          <label class="form-label">Ngày hẹn lắp đặt</label>
          <input type="text" :value="doc.expected_installation_date" class="form-input" readonly />
        </div>
        <div>
          <label class="form-label">Ngày nhận hàng</label>
          <input
            type="date"
            :value="doc.reception_date || ''"
            @change="trackChange('reception_date', ($event.target as HTMLInputElement).value)"
            :disabled="isReadonly"
            class="form-input"
          />
        </div>
        <div>
          <label class="form-label">Ngày giờ Bắt đầu Lắp đặt</label>
          <input type="text" :value="doc.installation_date || 'Chưa bắt đầu'" class="form-input" readonly />
        </div>
        <div>
          <label class="form-label">Tên Kỹ sư Hãng</label>
          <input
            type="text"
            :value="doc.vendor_engineer_name || ''"
            class="form-input"
            :readonly="isReadonly"
            placeholder="Nhập tên kỹ sư lắp đặt..."
            @change="trackChange('vendor_engineer_name', ($event.target as HTMLInputElement).value)"
          />
        </div>
      </div>

      <!-- Kết quả kiểm tra tổng thể (chỉ hiện ở các trạng thái kiểm tra) -->
      <div v-if="showOverallInspectionResult" class="form-row">
        <label for="field-overall-inspection-result" class="form-label">Kết quả Kiểm tra Tổng thể</label>
        <select
          id="field-overall-inspection-result"
          :value="doc.overall_inspection_result || ''"
          class="form-select"
          disabled
        >
          <option value="">-- Chưa có --</option>
          <option value="Pass">Pass</option>
          <option value="Fail">Fail</option>
          <option value="Conditional">Conditional</option>
        </select>
        <small class="form-hint text-gray-500">Được tính tự động từ kết quả kiểm tra an toàn</small>
      </div>

      <h3 class="text-base font-semibold text-gray-900 pb-2 border-b pt-4">Định danh Thiết bị</h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label class="form-label">Serial Number Hãng (NSX)</label>
          <input type="text" :value="doc.vendor_serial_no" class="form-input font-mono" readonly />
        </div>
        <div>
          <label class="form-label">Mã QR Nội bộ Bệnh viện</label>
          <div class="flex gap-2">
            <input type="text" :value="doc.internal_tag_qr || 'Chưa sinh'" class="form-input font-mono flex-1" readonly />
            <button
              v-if="doc.internal_tag_qr"
              class="btn-secondary px-3"
              title="Xem QR Label"
              @click="activeTab = 'output'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
              </svg>
            </button>
          </div>
        </div>
        <div>
          <label class="form-label">Mã BYT (Bộ Y tế)</label>
          <input
            type="text"
            :value="doc.custom_moh_code || ''"
            @change="trackChange('custom_moh_code', ($event.target as HTMLInputElement).value)"
            class="form-input"
            :readonly="isReadonly"
          />
        </div>
      </div>

      <!-- File upload section -->
      <h3 class="text-base font-semibold text-gray-900 pb-2 border-b pt-4">Tệp đính kèm</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label class="form-label">Ảnh mặt bằng lắp đặt</label>
          <div v-if="doc.site_photo" class="text-sm text-blue-600 mb-1">
            <a :href="doc.site_photo" target="_blank" class="underline">{{ doc.site_photo.split('/').pop() }}</a>
          </div>
          <input
            v-if="!isReadonly"
            type="file"
            accept="image/*"
            class="form-input text-sm"
            :disabled="uploading"
            @change="handleFileUpload($event, 'site_photo')"
          />
        </div>
        <div>
          <label class="form-label">Giấy phép BYT / Cục ATBXHN</label>
          <div v-if="doc.qa_license_doc" class="text-sm text-blue-600 mb-1">
            <a :href="doc.qa_license_doc" target="_blank" class="underline">{{ doc.qa_license_doc.split('/').pop() }}</a>
          </div>
          <input
            v-if="!isReadonly"
            type="file"
            accept=".pdf,.jpg,.png"
            class="form-input text-sm"
            :disabled="uploading"
            @change="handleFileUpload($event, 'qa_license_doc')"
          />
          <p v-if="doc.is_radiation_device && !doc.qa_license_doc" class="text-xs text-red-600 mt-1">
            Bắt buộc cho thiết bị bức xạ
          </p>
        </div>
      </div>

      <!-- Phân loại rủi ro -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        <div class="form-row">
          <label class="form-label">Phân loại rủi ro</label>
          <select
            :value="doc.risk_class || ''"
            @change="trackChange('risk_class', ($event.target as HTMLSelectElement).value)"
            :disabled="isReadonly"
            class="form-select"
          >
            <option value="">-- Chọn --</option>
            <option value="A">A — Rủi ro thấp</option>
            <option value="B">B — Rủi ro trung bình</option>
            <option value="C">C — Rủi ro cao</option>
            <option value="D">D — Rủi ro rất cao</option>
            <option value="Radiation">Phóng xạ</option>
          </select>
        </div>
      </div>

      <!-- Flags -->
      <div class="flex flex-wrap gap-4 pt-2">
        <label class="flex items-center gap-2 cursor-default">
          <input type="checkbox" :checked="Boolean(doc.is_radiation_device)" disabled class="rounded text-yellow-600" />
          <span class="text-sm text-gray-700">Thiết bị phát bức xạ / tia X</span>
        </label>
        <label class="flex items-center gap-2 cursor-default">
          <input type="checkbox" :checked="Boolean(doc.doa_incident)" disabled class="rounded text-red-600" />
          <span class="text-sm text-gray-700">Sự cố DOA</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            :checked="!!doc.facility_checklist_pass"
            @change="trackChange('facility_checklist_pass', ($event.target as HTMLInputElement).checked ? 1 : 0)"
            :disabled="isReadonly"
            class="form-checkbox"
          />
          <span class="text-sm text-gray-700">Cơ sở hạ tầng đạt yêu cầu (điện, nước, không gian)</span>
        </label>
      </div>

      <!-- QA Officer (chỉ hiện với thiết bị rủi ro cao) -->
      <div v-if="showQaOfficer" class="form-row">
        <label for="field-qa-officer" class="form-label">Nhân viên QA <span class="text-red-500">*</span></label>
        <input
          id="field-qa-officer"
          type="text"
          :value="doc.qa_officer || ''"
          @change="trackChange('qa_officer', ($event.target as HTMLInputElement).value)"
          :disabled="isReadonly"
          placeholder="User ID nhân viên QA"
          class="form-input"
        />
        <p class="form-hint text-orange-600">Bắt buộc với thiết bị Class C/D/Phóng xạ</p>
        <small class="form-hint">Nhập User ID (vd: user@hospital.com)</small>
      </div>

      <!-- Board Approver (chỉ hiện gần Clinical Release) -->
      <div v-if="showBoardApprover" class="form-row">
        <label for="field-board-approver" class="form-label">Người phê duyệt BGĐ <span class="text-red-500">*</span></label>
        <input
          id="field-board-approver"
          type="text"
          :value="doc.board_approver || ''"
          @change="trackChange('board_approver', ($event.target as HTMLInputElement).value)"
          :disabled="isReadonly"
          placeholder="User ID người phê duyệt"
          class="form-input"
        />
        <p class="form-hint text-red-600">BR-04-08: Bắt buộc trước khi phát hành lâm sàng</p>
        <small class="form-hint">Nhập User ID (vd: user@hospital.com)</small>
      </div>
    </div>

    <!-- Tab: Hồ sơ đi kèm -->
    <div v-show="activeTab === 'documents'" class="card">
      <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Bảng kiểm Hồ sơ Đi kèm</h3>
      <DocumentChecklist
        :documents="doc.commissioning_documents"
        :readonly="isReadonly"
        @update="onDocUpdate"
      />
    </div>

    <!-- Tab: Kiểm tra an toàn -->
    <div v-show="activeTab === 'safety'" class="card">
      <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Lưới Đo kiểm An toàn Điện</h3>
      <BaselineTestTable
        :tests="doc.baseline_tests"
        :readonly="isReadonly"
        @update="onTestUpdate"
      />
    </div>

    <!-- Tab: Kết quả triển khai -->
    <div v-show="activeTab === 'output'" class="space-y-6">
      <!-- Asset created -->
      <div class="card">
        <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Tài sản được tạo ra</h3>
        <div v-if="hasAsset" class="flex items-center gap-3 p-4 bg-green-50 rounded-lg border border-green-200">
          <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div class="flex-1">
            <p class="font-semibold text-green-800">Tài sản đã được tạo thành công</p>
            <p class="text-sm text-green-700 font-mono">{{ doc.final_asset }}</p>
          </div>
          <!-- Nút chuyển sang IMM-05 -->
          <a
            :href="`/documents?asset=${doc.final_asset}`"
            class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Cập nhật hồ sơ IMM-05
          </a>
        </div>
        <div v-else class="text-sm text-gray-500 italic p-4 bg-gray-50 rounded-lg">
          Tài sản sẽ được tạo tự động sau khi phiếu được Duyệt ở trạng thái Phát hành lâm sàng.
        </div>

        <!-- IMM-05 Compliance Widget (chỉ hiện khi có final_asset) -->
        <div v-if="hasAsset && imm05DocStatus !== undefined" class="mt-4">
          <div
            class="rounded-lg border p-4"
            :class="{
              'bg-green-50 border-green-200': imm05IsCompliant,
              'bg-yellow-50 border-yellow-200': !imm05IsCompliant && imm05DocStatus === 'Expiring_Soon',
              'bg-red-50 border-red-200': !imm05IsCompliant && imm05DocStatus !== 'Expiring_Soon',
            }"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-semibold text-gray-700">Trạng thái Hồ sơ IMM-05</span>
              <span
                class="text-xs font-bold px-2 py-0.5 rounded-full"
                :class="{
                  'bg-green-100 text-green-800': imm05IsCompliant,
                  'bg-yellow-100 text-yellow-800': !imm05IsCompliant && imm05DocStatus === 'Expiring_Soon',
                  'bg-red-100 text-red-800': !imm05IsCompliant && imm05DocStatus !== 'Expiring_Soon',
                }"
              >
                {{ imm05DocStatus ?? 'Chưa có dữ liệu' }}
              </span>
            </div>

            <!-- Progress bar -->
            <div class="flex items-center gap-3 mb-2">
              <div class="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="imm05IsCompliant ? 'bg-green-500' : 'bg-red-500'"
                  :style="`width: ${imm05Pct ?? 0}%`"
                />
              </div>
              <span class="text-xs text-gray-600 font-mono w-10 text-right">{{ imm05Pct ?? 0 }}%</span>
            </div>

            <!-- Thiếu hồ sơ -->
            <div v-if="imm05Missing && imm05Missing.length > 0" class="mt-2">
              <p class="text-xs text-red-700 font-medium mb-1">Thiếu hồ sơ bắt buộc:</p>
              <ul class="text-xs text-red-600 space-y-0.5 list-disc list-inside">
                <li v-for="m in imm05Missing" :key="m">{{ m }}</li>
              </ul>
            </div>

            <div class="mt-3 flex items-center justify-between">
              <p v-if="!imm05IsCompliant" class="text-xs text-red-700 font-medium">
                ⚠ Cần bổ sung hồ sơ trước khi Submit phiếu IMM-04
              </p>
              <button
                class="text-xs text-blue-600 hover:underline ml-auto"
                @click="emit('refresh-imm05')"
              >
                Làm mới
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Commissioning date & commissioned_by -->
      <div v-if="doc.commissioning_date || doc.commissioned_by" class="card">
        <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Thông tin Phát hành</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-if="doc.commissioning_date">
            <label for="field-commissioning-date" class="form-label">Ngày Phát hành</label>
            <input id="field-commissioning-date" type="text" :value="doc.commissioning_date" class="form-input" readonly />
          </div>
          <div v-if="doc.commissioned_by">
            <label for="field-commissioned-by" class="form-label">Người Phát hành</label>
            <input id="field-commissioned-by" type="text" :value="doc.commissioned_by" class="form-input" readonly />
          </div>
        </div>
      </div>

      <!-- QR Label -->
      <div v-if="doc.internal_tag_qr" class="card">
        <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Nhãn QR Thiết bị</h3>
        <QRLabel :name="doc.name" />
      </div>

      <!-- Amend reason -->
      <div v-if="doc.amended_from" class="card">
        <h3 class="text-base font-semibold text-gray-900 pb-2 border-b mb-4">Thông tin Sửa đổi</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Sửa đổi từ phiếu</label>
            <input type="text" :value="doc.amended_from" class="form-input font-mono" readonly />
          </div>
          <div>
            <label class="form-label">Lý do Sửa đổi</label>
            <textarea :value="doc.amend_reason" class="form-input" rows="3" readonly />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
