<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCommissioningStore } from '@/stores/imm04'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { qaNcTypeLabel } from '@/constants/labels'

const route = useRoute()
const store = useCommissioningStore()
const commissioningId = computed(() => route.params.id as string)

const loading = computed(() => store.loading)
const error = ref<string | null>(null)
const showCreateForm = ref(false)

const newNC = ref({
  nc_type: 'Other',
  severity: 'Minor' as 'Minor' | 'Major' | 'Critical',
  description: '',
})

// Close NC dialog state
const closingNcName = ref<string | null>(null)
const closeForm = ref({ root_cause: '', corrective_action: '' })

async function loadNCs(): Promise<void> {
  error.value = null
  await store.fetchNonConformances(commissioningId.value)
  if (store.error) error.value = store.error
}

async function createNC(): Promise<void> {
  if (!newNC.value.description.trim()) {
    error.value = 'Vui lòng nhập mô tả sự cố.'
    return
  }
  error.value = null
  const ok = await store.reportNonConformance(commissioningId.value, {
    nc_type: newNC.value.nc_type,
    severity: newNC.value.severity,
    description: newNC.value.description,
  })
  if (ok) {
    showCreateForm.value = false
    newNC.value = { nc_type: 'Other', severity: 'Minor', description: '' }
    await loadNCs()
  } else {
    error.value = store.error ?? 'Lỗi khi tạo sự không phù hợp'
  }
}

function openCloseDialog(ncName: string): void {
  closingNcName.value = ncName
  closeForm.value = { root_cause: '', corrective_action: '' }
}

function cancelClose(): void {
  closingNcName.value = null
}

async function confirmCloseNC(): Promise<void> {
  if (!closingNcName.value) return
  if (!closeForm.value.root_cause.trim() || !closeForm.value.corrective_action.trim()) {
    error.value = 'Vui lòng nhập nguyên nhân và hành động khắc phục.'
    return
  }
  error.value = null
  const ok = await store.doCloseNonConformance(
    closingNcName.value,
    closeForm.value.root_cause,
    closeForm.value.corrective_action,
  )
  if (ok) {
    closingNcName.value = null
    await loadNCs()
  } else {
    error.value = store.error ?? 'Lỗi khi đóng sự không phù hợp'
  }
}

const openCount = computed(() => store.openNcCount)

onMounted(loadNCs)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Sự không phù hợp"
      :subtitle="`Phiếu ${commissioningId}`"
      :back-to="`/commissioning/${commissioningId}`"
      back-label="← Phiếu lắp đặt"
      :breadcrumb="[
        { label: 'IMM-04 · Tiếp nhận', to: '/commissioning' },
        { label: commissioningId, to: `/commissioning/${commissioningId}` },
        { label: 'Không phù hợp' },
      ]"
    >
      <template #actions>
        <button class="btn-primary text-sm" @click="showCreateForm = !showCreateForm">
          + Báo cáo sự không phù hợp
        </button>
      </template>
    </PageHeader>

    <!-- Open NC warning -->
    <div
      v-if="openCount > 0"
      class="mb-4 flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
    >
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      Còn <strong class="mx-1">{{ openCount }}</strong> sự không phù hợp chưa đóng — thiết bị không thể phát hành.
    </div>

    <!-- Create form -->
    <div
      v-if="showCreateForm"
      class="bg-white rounded-xl shadow-sm border border-orange-200 p-6 mb-4"
    >
      <h2 class="text-sm font-semibold text-orange-900 uppercase tracking-wide mb-4">
        Báo cáo sự cố mới
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div>
          <label for="nc-type" class="block text-xs font-medium text-gray-700 mb-1">Loại không phù hợp</label>
          <select
            id="nc-type"
            v-model="newNC.nc_type"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
          >
            <option value="DOA">Hỏng ngay khi nhận</option>
            <option value="Missing">Thiếu phụ kiện</option>
            <option value="Crash">Hỏng vật lý</option>
            <option value="Technical">Lỗi kỹ thuật</option>
            <option value="Documentation">Thiếu tài liệu</option>
            <option value="Other">Khác</option>
          </select>
        </div>
        <div>
          <label for="nc-severity" class="block text-xs font-medium text-gray-700 mb-1">Mức độ</label>
          <select
            id="nc-severity"
            v-model="newNC.severity"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
          >
            <option value="Minor">Nhỏ</option>
            <option value="Major">Nghiêm trọng</option>
            <option value="Critical">Khẩn cấp</option>
          </select>
        </div>
      </div>
      <div class="mb-4">
        <label for="nc-description" class="block text-xs font-medium text-gray-700 mb-1">
          Mô tả sự cố <span class="text-red-500">*</span>
        </label>
        <textarea
          id="nc-description"
          v-model="newNC.description"
          rows="3"
          placeholder="Mô tả chi tiết sự cố..."
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
        />
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
          :disabled="store.loading"
          @click="createNC"
        >
          {{ store.loading ? 'Đang tạo...' : 'Tạo sự không phù hợp' }}
        </button>
        <button
          class="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
          @click="showCreateForm = false"
        >
          Hủy
        </button>
      </div>
    </div>

    <!-- Close NC dialog -->
    <div
      v-if="closingNcName"
      class="bg-white rounded-xl shadow-sm border border-green-200 p-6 mb-4"
    >
      <h2 class="text-sm font-semibold text-green-900 uppercase tracking-wide mb-4">
        Đóng sự không phù hợp — <span class="font-mono normal-case">{{ closingNcName }}</span>
      </h2>
      <div class="space-y-3 mb-4">
        <div>
          <label for="close-root-cause" class="block text-xs font-medium text-gray-700 mb-1">
            Nguyên nhân gốc rễ <span class="text-red-500">*</span>
          </label>
          <textarea
            id="close-root-cause"
            v-model="closeForm.root_cause"
            rows="2"
            placeholder="Mô tả nguyên nhân gốc rễ..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
          />
        </div>
        <div>
          <label for="close-corrective-action" class="block text-xs font-medium text-gray-700 mb-1">
            Hành động khắc phục <span class="text-red-500">*</span>
          </label>
          <textarea
            id="close-corrective-action"
            v-model="closeForm.corrective_action"
            rows="2"
            placeholder="Mô tả hành động khắc phục đã thực hiện..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
          />
        </div>
      </div>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
          @click="confirmCloseNC"
        >
          Xác nhận đóng sự không phù hợp
        </button>
        <button
          class="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition-colors"
          @click="cancelClose"
        >
          Hủy
        </button>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="mb-4 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600"
    >
      {{ error }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="space-y-3">
        <div
          v-for="i in 3"
          :key="i"
          class="h-16 bg-gray-100 rounded-lg animate-pulse"
        />
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="store.ncList.length === 0"
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center"
    >
      <svg
        class="w-12 h-12 text-green-400 mx-auto mb-3"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-gray-700 font-medium">Không có sự không phù hợp nào</p>
      <p class="text-gray-400 text-sm mt-1">Thiết bị chưa ghi nhận sự cố nào</p>
    </div>

    <!-- NC list -->
    <div v-else class="space-y-3">
      <div
        v-for="nc in store.ncList"
        :key="nc.name"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <span class="font-mono text-xs text-slate-500">{{ nc.name }}</span>
              <StatusBadge :state="nc.severity" />
              <StatusBadge :state="nc.resolution_status" />
              <span class="text-xs text-slate-400 bg-slate-50 px-2 py-0.5 rounded">
                {{ qaNcTypeLabel(nc.nc_type) }}
              </span>
            </div>
            <p class="text-sm text-gray-800">{{ nc.description }}</p>
            <p v-if="nc.root_cause" class="text-xs text-gray-500 mt-1">
              Nguyên nhân: {{ nc.root_cause }}
            </p>
            <p v-if="nc.resolution_note" class="text-xs text-gray-500 mt-1">
              Giải pháp: {{ nc.resolution_note }}
            </p>
            <p v-if="nc.closed_by" class="text-xs text-gray-400 mt-1">
              Đóng bởi: {{ nc.closed_by }}
              <span v-if="nc.closed_date"> · {{ nc.closed_date }}</span>
            </p>
          </div>
          <button
            v-if="nc.resolution_status === 'Open'"
            class="shrink-0 px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            @click="openCloseDialog(nc.name)"
          >
            Đóng sự không phù hợp
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
