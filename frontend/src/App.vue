<script setup lang="ts">
import { onMounted, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/common/AppLayout.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import RouteErrorBoundary from '@/components/common/RouteErrorBoundary.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'
import { useToast } from '@/composables/useToast'

const toast = useToast()

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth !== false && !auth.isAuthenticated) {
    const ok = await auth.fetchSession()
    if (!ok) { router.push({ name: 'Login' }) }
  }
})

// Bắt lỗi top-level để không bị blank page khi component con throw.
// RouteErrorBoundary đã render fallback UI trong route view; ở đây chỉ log + toast.
onErrorCaptured((err, _inst, info) => {
  const msg = (err as Error)?.message ?? 'Lỗi không xác định'
  console.error('[App.vue] top-level error:', { message: msg, info, err })
  toast.error(msg)
  return true
})

// Bắt unhandled promise rejection (ví dụ: API throw không try/catch trong handler)
window.addEventListener('unhandledrejection', (ev) => {
  const reason = ev.reason
  const msg = reason instanceof Error ? reason.message : String(reason)
  if (!msg) return
  // Không spam toast cho lỗi hệ thống đã được axios xử lý qua redirect (401/403)
  if (msg.includes('Đang chuyển hướng')) return
  console.error('[unhandledrejection]', reason)
  toast.error(msg)
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
      <!-- Authenticated: layout + ErrorBoundary -->
      <AppLayout v-if="auth.isAuthenticated">
        <RouteErrorBoundary>
          <RouterView v-slot="{ Component, route }">
            <component :is="Component" :key="route.fullPath" />
          </RouterView>
        </RouteErrorBoundary>
      </AppLayout>
      <!-- Unauthenticated: bare router view (Login page) -->
      <RouterView v-else />
    </template>
    <ToastContainer />
  </div>
</template>
