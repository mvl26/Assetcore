<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import { getAssetDocuments } from '@/api/imm05'
import CommissioningForm from '@/components/imm04/CommissioningForm.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const props = defineProps<{ id: string }>()

const router = useRouter()
const store = useCommissioningStore()

// ── IMM-05 compliance status cho final_asset ─────────────────────────────────
const imm05DocStatus = ref<string | null>(null)
const imm05Pct = ref(0)
const imm05Missing = ref<string[]>([])

const finalAsset = computed(() => store.currentDoc?.final_asset ?? null)

// compliant = Compliant hoặc Compliant (Exempt)
const imm05IsCompliant = computed(() =>
  imm05DocStatus.value === null ||
  imm05DocStatus.value === 'Compliant' ||
  imm05DocStatus.value === 'Compliant (Exempt)'
)

async function fetchImm05Status(asset: string) {
  try {
    const res = await getAssetDocuments(asset)
    if (res.success) {
      imm05DocStatus.value = res.data.document_status
      imm05Pct.value = res.data.completeness_pct
      imm05Missing.value = res.data.missing_required
    }
  } catch {
    // Non-blocking — IMM-05 chưa deploy hoặc lỗi mạng: im lặng
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

async function load() {
  await store.fetchDetail(props.id)
}

async function handleTransition(action: string) {
  await store.transitionState(props.id, action)
}

async function handleSubmit() {
  const ok = await store.submitDoc(props.id)
  if (ok) await load()
}

onMounted(load)
watch(() => props.id, load)

// Khi final_asset thay đổi (sau Submit), tự động fetch IMM-05 status
watch(finalAsset, (asset) => {
  if (asset) fetchImm05Status(asset)
}, { immediate: true })
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Breadcrumb -->
    <nav class="flex items-center gap-2 text-sm text-gray-500 mb-6">
      <button class="hover:text-gray-700 transition-colors" @click="router.push('/dashboard')">
        Dashboard
      </button>
      <span>/</span>
      <button class="hover:text-gray-700 transition-colors" @click="router.push('/commissioning')">
        Danh sách phiếu
      </button>
      <span>/</span>
      <span class="text-gray-900 font-mono font-medium">{{ id }}</span>
    </nav>

    <!-- Loading state -->
    <LoadingSpinner v-if="store.loading && !store.currentDoc" size="lg" label="Đang tải phiếu..." class="py-20" />

    <!-- Error state -->
    <div v-else-if="store.error && !store.currentDoc" class="card text-center py-16">
      <svg class="w-12 h-12 mx-auto text-red-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <p class="text-lg font-semibold text-gray-700 mb-2">Không thể tải phiếu</p>
      <p class="text-red-600 text-sm mb-6">{{ store.error }}</p>
      <div class="flex gap-3 justify-center">
        <button class="btn-secondary" @click="router.push('/commissioning')">
          Quay lại danh sách
        </button>
        <button class="btn-primary" @click="load">Thử lại</button>
      </div>
    </div>

    <!-- Main content -->
    <template v-else-if="store.currentDoc">
      <!-- Global error banner (after doc load) -->
      <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 -translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="store.error"
          class="mb-4 flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg"
        >
          <svg class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div class="flex-1">
            <p class="text-sm text-red-700">{{ store.error }}</p>
          </div>
          <button class="text-red-400 hover:text-red-600" @click="store.clearError">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </Transition>

      <!-- Loading overlay during transition -->
      <LoadingSpinner v-if="store.loading" size="md" label="Đang xử lý..." overlay />

      <!-- Form -->
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
