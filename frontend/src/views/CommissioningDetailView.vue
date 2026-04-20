<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import { useImm05Store } from '@/stores/imm05Store'
import CommissioningForm from '@/components/imm04/CommissioningForm.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const route  = useRoute()
const store  = useCommissioningStore()
const imm05  = useImm05Store()

const activeTab = computed(() => {
  if (route.name === 'CommissioningNC')       return 'nc'
  if (route.name === 'CommissioningTimeline') return 'timeline'
  return 'detail'
})

// IMM-05 compliance
const imm05DocStatus  = ref<string | null>(null)
const imm05Pct        = ref(0)
const imm05Missing    = ref<string[]>([])
const finalAsset      = computed(() => store.currentDoc?.final_asset ?? null)
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

async function load() { await store.fetchDetail(props.id) }

async function handleTransition(action: string) { await store.transitionState(props.id, action) }
async function handleSubmit() { const ok = await store.submitDoc(props.id); if (ok) await load() }

onMounted(load)
watch(() => props.id, load)
watch(finalAsset, (asset) => { if (asset) fetchImm05Status(asset) }, { immediate: true })
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Breadcrumb -->
    <nav class="flex items-center gap-1.5 text-xs text-slate-400 mb-6">
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/dashboard')">
        Dashboard
      </button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <button class="hover:text-slate-600 transition-colors" @click="router.push('/commissioning')">
        Danh sách phiếu
      </button>
      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-mono font-semibold text-slate-700">{{ id }}</span>
      <template v-if="store.currentDoc">
        <StatusBadge :state="store.currentDoc.workflow_state" size="xs" class="ml-1" />
      </template>
    </nav>

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
        :class="activeTab === 'detail'
          ? 'text-brand-600'
          : 'text-slate-500 hover:text-slate-700'"
        @click="router.push(`/commissioning/${id}`)"
      >
        Chi tiết phiếu
        <span v-if="activeTab === 'detail'"
              class="absolute inset-x-0 bottom-0 h-0.5 rounded-t bg-brand-600" />
      </button>
      <button
        class="relative px-4 py-2.5 text-sm font-medium transition-colors duration-150 flex items-center gap-1.5"
        :class="activeTab === 'nc'
          ? 'text-brand-600'
          : 'text-slate-500 hover:text-slate-700'"
        @click="router.push(`/commissioning/${id}/nc`)"
      >
        Non Conformance
        <span
          v-if="store.openNcCount > 0"
          class="inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold"
        >{{ store.openNcCount }}</span>
        <span v-if="activeTab === 'nc'"
              class="absolute inset-x-0 bottom-0 h-0.5 rounded-t bg-brand-600" />
      </button>
      <button
        class="relative px-4 py-2.5 text-sm font-medium transition-colors duration-150"
        :class="activeTab === 'timeline'
          ? 'text-brand-600'
          : 'text-slate-500 hover:text-slate-700'"
        @click="router.push(`/commissioning/${id}/timeline`)"
      >
        Lịch sử
        <span v-if="activeTab === 'timeline'"
              class="absolute inset-x-0 bottom-0 h-0.5 rounded-t bg-brand-600" />
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

      <CommissioningForm
        :doc="store.currentDoc"
        :imm05-doc-status="imm05DocStatus"
        :imm05-pct="imm05Pct"
        :imm05-missing="imm05Missing"
        :imm05-is-compliant="imm05IsCompliant"
        @transition="handleTransition"
        @submit="handleSubmit"
        @refresh-imm05="finalAsset ? fetchImm05Status(finalAsset) : undefined"
      />
    </template>

  </div>
</template>
