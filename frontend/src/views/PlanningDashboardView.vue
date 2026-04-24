<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center gap-3 mb-6">
      <button
        class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
        @click="router.back()"
      >
        ← Quay lại
      </button>
    </div>
    <h1 class="text-xl font-semibold text-gray-800 mb-2">Tổng quan Kế hoạch</h1>
    <p class="text-sm text-gray-500 mb-6">Route: <code class="bg-gray-100 px-1 rounded">/planning/dashboard</code></p>
    <div class="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center">
      <p class="text-gray-400 text-sm">Giao diện đang phát triển — Wave 2 Sprint 1</p>
    </div>
  </div>
</template>
