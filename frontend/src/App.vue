<script setup lang="ts">
import { onMounted, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/common/AppLayout.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import NotificationModal from '@/components/common/NotificationModal.vue'
import RouteErrorBoundary from '@/components/common/RouteErrorBoundary.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'
import { useNotify } from '@/composables/useNotify'

const notify = useNotify()

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  const currentRoute = router.currentRoute.value
  if (currentRoute.meta.requiresAuth === false) return
  // bootstrap() bật cờ `auth.bootstrapping` (KHÔNG phải `loading`) trong suốt
  // phiên khôi phục lần đầu → full-screen spinner "Đang khởi tạo..." chỉ đè màn
  // này, KHÔNG đè /login khi login-submit. Chưa auth → khôi phục cookie-session;
  // đã auth → re-hydrate role/persona/caps ở nền chống persona stale.
  const ok = await auth.bootstrap()
  if (!ok) router.push({ name: 'Login' })
})

// Bắt lỗi top-level để không bị blank page khi component con throw.
// RouteErrorBoundary đã render fallback UI trong route view; ở đây chỉ log + toast.
// Phase 1 notification framework: dùng notify.fromError → hydrate registry +
// route critical sang modal.
onErrorCaptured((err, _inst, info) => {
  console.error('[App.vue] top-level error:', { info, err })
  notify.fromError(err)
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
  notify.fromError(reason)
})
</script>

<template>
  <div class="min-h-full">
    <!-- Full-screen overlay CHỈ cho bootstrap/session-restore (App.vue onMounted).
         KHÔNG bật theo `auth.loading` (login-submit) — nếu không sẽ remount /login
         đang submit → mất field + banner (APP-AUTH-01/02). -->
    <template v-if="auth.bootstrapping && !auth.isAuthenticated">
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
    <NotificationModal />
  </div>
</template>
