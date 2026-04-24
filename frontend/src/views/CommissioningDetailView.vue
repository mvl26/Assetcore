<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import { useImm05Store } from '@/stores/imm05Store'
import { usePermissions } from '@/composables/usePermissions'
import { useToast } from '@/composables/useToast'
import CommissioningForm from '@/components/imm04/CommissioningForm.vue'
import ApprovalPanel from '@/components/imm04/ApprovalPanel.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { getGateStatus, approveClinicalRelease } from '@/api/imm04'
import type { GateStatus } from '@/api/imm04'

const props  = defineProps<{ id: string }>()
const router = useRouter()
const route  = useRoute()
const store  = useCommissioningStore()
const imm05  = useImm05Store()
const perms  = usePermissions()
const toast  = useToast()

// ─── Edit mode ───────────────────────────────────────────────────────────────
const editMode = ref(false)

function enterEdit() { editMode.value = true }
function cancelEdit() {
  editMode.value = false
  store.clearError()
}

// ─── Confirm modal ───────────────────────────────────────────────────────────
type ConfirmIntent = 'delete' | 'cancel'
const confirmIntent  = ref<ConfirmIntent | null>(null)
const confirmPending = ref(false)

function openConfirm(intent: ConfirmIntent) { confirmIntent.value = intent }
function closeConfirm() { confirmIntent.value = null }

const confirmConfig = computed(() => {
  if (confirmIntent.value === 'delete') return {
    title:   'Xóa phiếu lắp đặt',
    message: `Phiếu ${props.id} sẽ bị xóa vĩnh viễn và không thể khôi phục. Bạn có chắc chắn?`,
    confirm: 'Xóa phiếu',
    variant: 'red' as const,
  }
  return {
    title:   'Hủy phiếu đã duyệt',
    message: `Phiếu ${props.id} sẽ chuyển sang trạng thái Đã hủy (docstatus = 2). Không thể hoàn tác. Tiếp tục?`,
    confirm: 'Hủy phiếu',
    variant: 'red' as const,
  }
})

async function executeConfirm() {
  confirmPending.value = true
  if (confirmIntent.value === 'delete') {
    const ok = await store.deleteDoc(props.id)
    confirmPending.value = false
    closeConfirm()
    if (ok) {
      toast.success('Đã xóa phiếu thành công.')
      router.push('/commissioning')
    } else {
      toast.error(store.error ?? 'Không thể xóa phiếu. Vui lòng thử lại.')
    }
  } else if (confirmIntent.value === 'cancel') {
    const ok = await store.cancelDoc(props.id)
    confirmPending.value = false
    closeConfirm()
    if (ok) {
      toast.success('Đã hủy phiếu thành công.')
    } else {
      toast.error(store.error ?? 'Không thể hủy phiếu. Vui lòng thử lại.')
    }
  }
}

// ─── Toolbar computed ────────────────────────────────────────────────────────
const isDraft     = computed(() => (store.currentDoc?.docstatus ?? -1) === 0)
const isSubmitted = computed(() => (store.currentDoc?.docstatus ?? -1) === 1)
const isCancelled = computed(() => (store.currentDoc?.docstatus ?? -1) === 2)
const canCancel   = computed(() => isSubmitted.value && (perms.isAdmin.value || perms.isQA.value))

// ─── Tabs ────────────────────────────────────────────────────────────────────
const activeTab = computed(() => {
  if (route.name === 'CommissioningNC')       return 'nc'
  if (route.name === 'CommissioningTimeline') return 'timeline'
  return 'detail'
})

// ─── IMM-05 compliance ───────────────────────────────────────────────────────
const imm05DocStatus   = ref<string | null>(null)
const imm05Pct         = ref(0)
const imm05Missing     = ref<string[]>([])
const finalAsset       = computed(() => store.currentDoc?.final_asset ?? null)
const imm05IsCompliant = computed(() =>
  imm05DocStatus.value === null ||
  imm05DocStatus.value === 'Compliant' ||
  imm05DocStatus.value === 'Compliant (Exempt)',
)

async function fetchImm05Status(asset: string) {
  await imm05.fetchAssetDocuments(asset)
  imm05DocStatus.value = imm05.assetDocumentStatus || null
  imm05Pct.value       = imm05.assetCompletenessPct
  imm05Missing.value   = imm05.missingRequired
}

// ─── Gate status ─────────────────────────────────────────────────────────────
const defaultGateStatus: GateStatus = {
  g01_docs: false, g02_facility: false, g03_baseline: false,
  g04_radiation: false, g05_nc: false, g06_approver: false,
}
const gateStatus  = ref<GateStatus>({ ...defaultGateStatus })
const panelSaving = ref(false)

async function loadGateStatus() {
  try {
    gateStatus.value = await getGateStatus(props.id)
  } catch {
    gateStatus.value = { ...defaultGateStatus }
  }
}

async function load() {
  editMode.value = false
  await Promise.all([store.fetchDetail(props.id), loadGateStatus()])
}

async function handleTransition(action: string) {
  const ok = await store.transitionState(props.id, action)
  if (ok) {
    toast.success('Đã chuyển trạng thái thành công.')
    await loadGateStatus()
  } else {
    toast.error(store.error ?? 'Không thể thực hiện hành động.')
  }
}

async function handleTransitionFromPanel(action: string) {
  panelSaving.value = true
  const ok = await store.transitionState(props.id, action)
  panelSaving.value = false
  if (ok) {
    toast.success('Đã chuyển trạng thái thành công.')
    await Promise.all([store.fetchDetail(props.id), loadGateStatus()])
  } else {
    toast.error(store.error ?? 'Không thể thực hiện hành động.')
  }
}

async function handleApprove(boardApprover: string, remarks: string) {
  panelSaving.value = true
  try {
    await approveClinicalRelease(props.id, boardApprover, remarks)
    toast.success('Đã phê duyệt phát hành lâm sàng thành công.')
    await Promise.all([store.fetchDetail(props.id), loadGateStatus()])
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Không thể phê duyệt. Vui lòng thử lại.')
  } finally {
    panelSaving.value = false
  }
}

async function handleFieldUpdate(field: string, value: unknown) {
  const ok = await store.saveDoc(props.id, { [field]: value })
  if (ok) {
    await Promise.all([store.fetchDetail(props.id), loadGateStatus()])
  } else {
    toast.error(store.error ?? 'Không thể lưu thay đổi.')
  }
}

async function handleSubmit() {
  const ok = await store.submitDoc(props.id)
  if (ok) {
    toast.success('Phiếu đã được Submit và kích hoạt tài sản thành công!')
    await load()
  } else {
    toast.error(store.error ?? 'Không thể Submit phiếu.')
  }
}

function handleSaved() {
  editMode.value = false
  toast.success('Đã lưu thay đổi thành công.')
}

onMounted(load)
watch(() => props.id, load)
watch(finalAsset, (asset) => { if (asset) fetchImm05Status(asset) }, { immediate: true })
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Toast notifications -->
    <Teleport to="body">
      <div class="fixed top-4 right-4 z-[60] flex flex-col gap-2 pointer-events-none">
        <TransitionGroup
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0 translate-x-4"
          enter-to-class="opacity-100 translate-x-0"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0 translate-x-4"
        >
          <div
            v-for="t in toast.toasts.value"
            :key="t.id"
            class="pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl shadow-lg text-sm max-w-sm"
            :class="{
              'bg-green-600 text-white':  t.type === 'success',
              'bg-red-600 text-white':    t.type === 'error',
              'bg-amber-500 text-white':  t.type === 'warning',
              'bg-slate-800 text-white':  t.type === 'info',
            }"
          >
            <svg v-if="t.type === 'success'" class="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <svg v-else-if="t.type === 'error'" class="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <svg v-else class="w-4 h-4 mt-0.5 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="flex-1">{{ t.message }}</span>
          </div>
        </TransitionGroup>
      </div>
    </Teleport>

    <!-- Confirm Modal -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="confirmIntent"
             class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
             @mousedown.self="closeConfirm">
          <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <div class="flex items-start gap-4">
              <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round"
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div>
                <h3 class="text-base font-semibold text-slate-900 mb-1">{{ confirmConfig.title }}</h3>
                <p class="text-sm text-slate-600">{{ confirmConfig.message }}</p>
              </div>
            </div>
            <div class="flex gap-3 mt-6 justify-end">
              <button class="btn-ghost" :disabled="confirmPending" @click="closeConfirm">Không, giữ lại</button>
              <button
                class="btn text-white"
                :class="confirmConfig.variant === 'red' ? 'bg-red-600 hover:bg-red-700' : 'bg-amber-600 hover:bg-amber-700'"
                :disabled="confirmPending"
                @click="executeConfirm"
              >
                <svg v-if="confirmPending" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                {{ confirmPending ? 'Đang xử lý...' : confirmConfig.confirm }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/dashboard')">Dashboard</button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/commissioning')">Danh sách phiếu</button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-mono font-semibold text-slate-700">{{ id }}</span>
      <template v-if="store.currentDoc">
        <StatusBadge :state="store.currentDoc.workflow_state" size="xs" class="ml-1" />
      </template>
    </nav>

    <!-- ── ACTION TOOLBAR ─────────────────────────────────────────────────── -->
    <div v-if="store.currentDoc" class="flex flex-wrap items-center justify-between gap-3 mb-5">

      <!-- Left: context label -->
      <div class="flex items-center gap-2 text-sm">
        <template v-if="editMode">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-semibold">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Chế độ chỉnh sửa
          </span>
        </template>
        <template v-else-if="isCancelled">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 text-xs font-semibold">
            Phiếu đã hủy — Chỉ đọc
          </span>
        </template>
      </div>

      <!-- Right: action buttons -->
      <div class="flex flex-wrap items-center gap-2">

        <!-- DRAFT (docstatus=0): Edit / Delete -->
        <template v-if="isDraft && !editMode">
          <button class="btn-secondary flex items-center gap-1.5" @click="enterEdit">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Sửa
          </button>
          <button
            class="btn flex items-center gap-1.5 bg-red-50 text-red-700 border border-red-200 hover:bg-red-100"
            @click="openConfirm('delete')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Xóa phiếu
          </button>
        </template>

        <!-- DRAFT + editMode: Cancel edit -->
        <template v-if="isDraft && editMode">
          <button class="btn-ghost flex items-center gap-1.5" @click="cancelEdit">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Hủy bỏ
          </button>
        </template>

        <!-- SUBMITTED (docstatus=1): Cancel document (role-gated) -->
        <template v-if="canCancel">
          <button
            class="btn flex items-center gap-1.5 bg-red-50 text-red-700 border border-red-200 hover:bg-red-100"
            @click="openConfirm('cancel')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round"
                    d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            Hủy phiếu
          </button>
        </template>

      </div>
    </div>

    <!-- IMM-05 compliance banner -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
    >
      <div
        v-if="finalAsset && !imm05IsCompliant"
        class="flex items-center gap-3 px-4 py-3 rounded-xl border mb-5 text-sm"
        style="background: #fff7ed; border-color: #fed7aa"
      >
        <svg class="w-4 h-4 text-amber-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div class="flex-1">
          <span class="font-semibold text-amber-800">IMM-05:</span>
          <span class="text-amber-700 ml-1">
            {{ imm05DocStatus }} — {{ imm05Pct }}% đầy đủ.
            <span v-if="imm05Missing.length">
              Thiếu: {{ imm05Missing.slice(0, 2).join(', ') }}
              <span v-if="imm05Missing.length > 2"> +{{ imm05Missing.length - 2 }} hồ sơ khác</span>.
            </span>
          </span>
        </div>
        <button class="text-xs font-semibold text-amber-600 hover:text-amber-800 transition-colors shrink-0"
                @click="router.push(`/documents?asset=${finalAsset}`)">
          Quản lý hồ sơ →
        </button>
      </div>
    </Transition>

    <!-- Tabs -->
    <div class="flex items-end gap-0 mb-6 border-b border-slate-200">
      <button
        class="relative px-4 py-2.5 text-sm font-medium transition-colors duration-150"
        :class="activeTab === 'detail' ? 'text-brand-600' : 'text-slate-500 hover:text-slate-700'"
        @click="router.push(`/commissioning/${id}`)"
      >
        Chi tiết phiếu
        <span v-if="activeTab === 'detail'" class="absolute inset-x-0 bottom-0 h-0.5 rounded-t bg-brand-600" />
      </button>
      <button
        class="relative px-4 py-2.5 text-sm font-medium transition-colors duration-150 flex items-center gap-1.5"
        :class="activeTab === 'nc' ? 'text-brand-600' : 'text-slate-500 hover:text-slate-700'"
        @click="router.push(`/commissioning/${id}/nc`)"
      >
        Non Conformance
        <span
          v-if="store.openNcCount > 0"
          class="inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold"
        >{{ store.openNcCount }}</span>
        <span v-if="activeTab === 'nc'" class="absolute inset-x-0 bottom-0 h-0.5 rounded-t bg-brand-600" />
      </button>
      <button
        class="relative px-4 py-2.5 text-sm font-medium transition-colors duration-150"
        :class="activeTab === 'timeline' ? 'text-brand-600' : 'text-slate-500 hover:text-slate-700'"
        @click="router.push(`/commissioning/${id}/timeline`)"
      >
        Lịch sử
        <span v-if="activeTab === 'timeline'" class="absolute inset-x-0 bottom-0 h-0.5 rounded-t bg-brand-600" />
      </button>
    </div>

    <!-- Loading skeleton -->
    <SkeletonLoader v-if="store.loading && !store.currentDoc" variant="form" />

    <!-- Error -->
    <div v-else-if="store.error && !store.currentDoc" class="card text-center py-16">
      <div class="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
        <svg class="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <p class="text-base font-semibold text-slate-700 mb-1">Không thể tải phiếu</p>
      <p class="text-sm text-red-500 mb-6">{{ store.error }}</p>
      <div class="flex gap-3 justify-center">
        <button class="btn-secondary" @click="router.push('/commissioning')">Quay lại danh sách</button>
        <button class="btn-primary" @click="load">Thử lại</button>
      </div>
    </div>

    <!-- Main content -->
    <template v-else-if="store.currentDoc">

      <!-- Inline error (after load) -->
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="store.error" class="alert-error mb-5">
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span class="flex-1 text-sm">{{ store.error }}</span>
          <button class="text-red-400 hover:text-red-600 transition-colors" @click="store.clearError">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </Transition>

      <!-- Processing overlay -->
      <div v-if="store.loading"
           class="fixed inset-0 z-50 flex items-center justify-center"
           style="background: rgba(15,23,42,0.25)">
        <div class="bg-white rounded-xl px-6 py-4 shadow-dropdown flex items-center gap-3">
          <svg class="w-5 h-5 text-brand-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <span class="text-sm font-medium text-slate-700">Đang xử lý...</span>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <!-- Main form — takes 2/3 on wide screens -->
        <div class="xl:col-span-2">
          <CommissioningForm
            :doc="store.currentDoc"
            :edit-mode="editMode"
            :imm05-doc-status="imm05DocStatus"
            :imm05-pct="imm05Pct"
            :imm05-missing="imm05Missing"
            :imm05-is-compliant="imm05IsCompliant"
            @transition="handleTransition"
            @submit="handleSubmit"
            @saved="handleSaved"
            @refresh-imm05="finalAsset ? fetchImm05Status(finalAsset) : undefined"
          />
        </div>

        <!-- Approval panel — sidebar on wide screens -->
        <div class="xl:col-span-1">
          <ApprovalPanel
            :doc="store.currentDoc"
            :gate-status="gateStatus"
            :saving="panelSaving"
            @transition="handleTransitionFromPanel"
            @approve="handleApprove"
            @update-field="handleFieldUpdate"
            @refresh="load"
          />
        </div>
      </div>
    </template>

  </div>
</template>
