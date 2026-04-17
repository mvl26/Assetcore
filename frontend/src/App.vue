<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/common/AppLayout.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth !== false && !auth.isAuthenticated) {
    const ok = await auth.fetchSession()
    if (!ok) { router.push({ name: 'Login' }) }
  }
})
</script>

<template>
  <div class="min-h-full">
    <template v-if="auth.loading && !auth.isAuthenticated">
      <div class="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" label="Đang khởi tạo..." />
      </div>
    </template>
    <template v-else>
      <!-- Authenticated: use layout with sidebar -->
      <AppLayout v-if="auth.isAuthenticated">
        <RouterView />
      </AppLayout>
      <!-- Unauthenticated: bare router view (Login page) -->
      <RouterView v-else />
    </template>
  </div>
</template>
