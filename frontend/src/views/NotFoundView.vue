<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center p-6">
    <div class="max-w-md text-center space-y-4">
      <div class="text-6xl font-display font-bold text-blue-600">404</div>
      <h1 class="text-xl font-semibold text-gray-800">Không tìm thấy trang</h1>
      <p class="text-sm text-gray-500">
        Đường dẫn <code class="px-1.5 py-0.5 bg-gray-100 rounded text-xs">{{ route.fullPath }}</code> không tồn tại.
      </p>
      <div class="flex gap-3 justify-center pt-2">
        <button class="btn-ghost" @click="router.back()">← Quay lại</button>
        <button class="btn-primary" @click="router.push('/dashboard')">Về Dashboard</button>
      </div>
    </div>
  </div>
</template>
