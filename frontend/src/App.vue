<script setup lang="ts">
import { onMounted, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/common/AppLayout.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import RouteErrorBoundary from '@/components/common/RouteErrorBoundary.vue'

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth !== false && !auth.isAuthenticated) {
    const ok = await auth.fetchSession()
    if (!ok) { router.push({ name: 'Login' }) }
  }
})

// Bắt lỗi top-level để không bị blank page khi component con throw
onErrorCaptured((err, _inst, info) => {
  console.error('[App.vue] top-level error:', { message: (err as Error)?.message, info, err })
  return true
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
      <!-- Authenticated: layout + Suspense boundary cho async setup + ErrorBoundary -->
      <AppLayout v-if="auth.isAuthenticated">
        <RouteErrorBoundary>
          <Suspense timeout="0">
            <RouterView v-slot="{ Component, route }">
              <component :is="Component" :key="route.fullPath" />
            </RouterView>
            <template #fallback>
              <div class="flex items-center justify-center py-20">
                <LoadingSpinner size="md" label="Đang tải trang..." />
              </div>
            </template>
          </Suspense>
        </RouteErrorBoundary>
      </AppLayout>
      <!-- Unauthenticated: bare router view (Login page) -->
      <RouterView v-else />
    </template>
  </div>
</template>
