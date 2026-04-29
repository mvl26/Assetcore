<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const attempted = (route.query.forbidden as string) || ''
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6">
    <div class="max-w-md w-full text-center space-y-4">
      <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-2xl">
        <span class="text-3xl">🔒</span>
      </div>
      <h1 class="text-2xl font-semibold text-slate-800">Không đủ quyền truy cập</h1>
      <p class="text-slate-500 text-sm">
        Bạn không có quyền vào trang này.
        <template v-if="attempted">
          <br><code class="text-xs bg-slate-100 px-2 py-0.5 rounded">{{ attempted }}</code>
        </template>
      </p>
      <p class="text-slate-400 text-xs">Liên hệ quản trị viên nếu bạn cần quyền này.</p>
      <div class="flex justify-center gap-2 pt-2">
        <button class="btn-ghost text-sm" @click="router.push('/')">← Quay lại</button>
        <button class="btn-primary text-sm" @click="router.push('/dashboard')">Về Dashboard</button>
      </div>
    </div>
  </div>
</template>
