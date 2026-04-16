<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppHeader from '@/components/common/AppHeader.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth !== false && !auth.isAuthenticated) {
    const ok = await auth.fetchSession()
    if (!ok) {
      router.push({ name: 'Login' })
    }
  }
})
</script>

<template>
  <div class="min-h-full">
    <template v-if="auth.loading && !auth.isAuthenticated">
      <div class="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" label="Đang khởi tạo hệ thống..." />
      </div>
    </template>

    <template v-else>
      <AppHeader v-if="auth.isAuthenticated" />
      <main :class="auth.isAuthenticated ? 'pt-16' : ''">
        <RouterView />
      </main>
    </template>
  </div>
</template>
