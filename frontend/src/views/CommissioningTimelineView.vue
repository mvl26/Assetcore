<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCommissioningStore } from '@/stores/commissioning'
import { formatDatetime } from '@/utils/docUtils'
import type { LifecycleEvent } from '@/types/imm04'

const route = useRoute()
const router = useRouter()
const store = useCommissioningStore()
const commissioningId = computed(() => route.params.id as string)

const events = ref<LifecycleEvent[]>([])
const loading = computed(() => store.loading)
const error = ref<string | null>(null)

const eventIconMap: Record<string, { svg: string; color: string }> = {
  'State Transition': {
    color: 'border-blue-300 bg-blue-50',
    svg: 'M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99',
  },
  Release: {
    color: 'border-green-300 bg-green-50',
    svg: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  Cancel: {
    color: 'border-red-300 bg-red-50',
    svg: 'M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  'Document Upload': {
    color: 'border-purple-300 bg-purple-50',
    svg: 'M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13',
  },
  'Non-Conformance': {
    color: 'border-orange-300 bg-orange-50',
    svg: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z',
  },
  'Baseline Test': {
    color: 'border-teal-300 bg-teal-50',
    svg: 'M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5',
  },
  Identification: {
    color: 'border-indigo-300 bg-indigo-50',
    svg: 'M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z M6 6h.008v.008H6V6z',
  },
  Handover: {
    color: 'border-gray-300 bg-gray-50',
    svg: 'M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75',
  },
}

const defaultIcon = {
  color: 'border-gray-200 bg-white',
  svg: 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z',
}

async function load(): Promise<void> {
  error.value = null
  await store.fetchTimeline(commissioningId.value)
  if (store.error) {
    error.value = store.error
  } else {
    events.value = store.timeline.slice().sort(
      (a, b) => new Date(b.event_timestamp).getTime() - new Date(a.event_timestamp).getTime(),
    )
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Back button -->
    <button
      class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
      @click="router.back()"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
      </svg>
      Quay lại
    </button>

    <!-- Header card -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <h1 class="text-xl font-bold text-gray-900">Lịch sử vòng đời</h1>
          <p class="text-sm text-gray-500 mt-1">
            <span class="font-mono font-medium text-gray-700">{{ commissioningId }}</span>
            <template v-if="store.currentDoc">
              <span class="mx-1 text-gray-300">·</span>
              {{ store.currentDoc?.master_item }}
              <template v-if="store.currentDoc?.vendor_serial_no">
                <span class="mx-1 text-gray-300">·</span>
                SN: {{ store.currentDoc?.vendor_serial_no }}
              </template>
            </template>
          </p>
        </div>
        <span
          v-if="store.currentDoc"
          class="shrink-0 inline-block px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800"
        >
          {{ store.currentDoc?.workflow_state }}
        </span>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="mb-4 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600"
    >
      {{ error }}
      <button class="ml-3 underline hover:no-underline" @click="load">Thử lại</button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div
        v-for="i in 4"
        :key="i"
        class="flex gap-4"
      >
        <div class="w-12 h-12 rounded-full bg-gray-100 animate-pulse shrink-0" />
        <div class="flex-1 bg-white rounded-xl border border-gray-200 p-4 h-16 animate-pulse" />
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!loading && events.length === 0"
      class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center"
    >
      <svg
        class="w-12 h-12 text-gray-300 mx-auto mb-3"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
      <p class="text-gray-700 font-medium">Chưa có sự kiện nào</p>
      <p class="text-gray-400 text-sm mt-1">Audit trail sẽ xuất hiện sau khi thực hiện các thao tác</p>
    </div>

    <!-- Timeline -->
    <div v-else class="relative">
      <!-- Vertical connecting line -->
      <div class="absolute left-6 top-6 bottom-6 w-0.5 bg-gray-200 -translate-x-0.5" />

      <div class="space-y-4">
        <div
          v-for="(event, idx) in events"
          :key="idx"
          class="relative flex gap-4"
        >
          <!-- Icon node -->
          <div
            :class="[
              'relative z-10 shrink-0 w-12 h-12 rounded-full border-2 flex items-center justify-center',
              (eventIconMap[event.event_type] ?? defaultIcon).color,
            ]"
          >
            <svg
              class="w-5 h-5 text-current"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                :d="(eventIconMap[event.event_type] ?? defaultIcon).svg"
              />
            </svg>
          </div>

          <!-- Event card -->
          <div class="flex-1 bg-white border border-gray-200 rounded-xl p-4 shadow-sm min-w-0">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <p class="font-semibold text-gray-900 text-sm">{{ event.event_type }}</p>

                <!-- State transition badges -->
                <div
                  v-if="event.from_status || event.to_status"
                  class="flex items-center gap-1.5 mt-1.5 flex-wrap"
                >
                  <span
                    v-if="event.from_status"
                    class="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded font-mono"
                  >
                    {{ event.from_status }}
                  </span>
                  <svg
                    v-if="event.from_status && event.to_status"
                    class="w-3 h-3 text-gray-400 shrink-0"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                  <span
                    v-if="event.to_status"
                    class="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded font-mono font-medium"
                  >
                    {{ event.to_status }}
                  </span>
                </div>

                <p v-if="event.remarks" class="text-xs text-gray-500 mt-1.5 leading-relaxed">
                  {{ event.remarks }}
                </p>
              </div>

              <!-- Timestamp & actor -->
              <div class="shrink-0 text-right text-xs text-gray-400 space-y-0.5">
                <p class="font-medium text-gray-600">{{ formatDatetime(event.event_timestamp) }}</p>
                <p>{{ event.actor }}</p>
                <p v-if="event.ip_address" class="font-mono">{{ event.ip_address }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
