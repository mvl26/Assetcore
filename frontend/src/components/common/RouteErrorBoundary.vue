<script setup lang="ts">
import { ref, onErrorCaptured, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const err = ref<Error | null>(null)

onErrorCaptured((e) => {
  console.error('[RouteErrorBoundary] caught render error:', e)
  err.value = e as Error
  // Return false để stop propagation — Vue sẽ không crash cả app
  return false
})

// Reset mỗi khi route đổi
watch(() => route.fullPath, () => { err.value = null })

function retry() {
  err.value = null
  router.go(0)
}

function goHome() {
  err.value = null
  router.push('/dashboard')
}
</script>

<template>
  <div v-if="err" class="p-8 max-w-2xl mx-auto mt-10">
    <div class="bg-red-50 border border-red-200 rounded-xl p-6">
      <div class="flex items-start gap-3 mb-4">
        <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0 text-xl">⚠️</div>
        <div class="flex-1">
          <h2 class="text-lg font-semibold text-red-800 mb-1">Trang gặp lỗi khi tải</h2>
          <p class="text-sm text-red-700">{{ err.message || 'Lỗi không xác định' }}</p>
          <p class="text-xs text-red-500 mt-2 font-mono">URL: {{ route.fullPath }}</p>
        </div>
      </div>
      <pre v-if="err.stack" class="mt-3 text-[11px] bg-white rounded p-3 max-h-40 overflow-auto text-slate-600">{{ err.stack }}</pre>
      <div class="flex gap-3 mt-5">
        <button class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium" @click="retry">
          Tải lại trang
        </button>
        <button class="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50" @click="goHome">
          Về Dashboard
        </button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>
