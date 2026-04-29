// Copyright (c) 2026, AssetCore Team
// App bootstrap

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPersistedState from 'pinia-plugin-persistedstate'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import App from './App.vue'
import router from './router'
import { i18n } from './locales'
import './assets/styles/main.css'
import axios from 'axios'
import { setCsrfToken } from '@/api/axios'
import { vPermission } from '@/directives/permission'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,   // 5 min — reuse cached data within a session
      gcTime:    10 * 60 * 1000,  // 10 min — keep in memory after last subscriber
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const app = createApp(App)

// Global Vue error handler — log tất cả lỗi component, ngăn blank page silent
app.config.errorHandler = (err, instance, info) => {
   
  console.error('[Vue errorHandler]', { message: (err as Error)?.message, info, err, component: instance?.$options?.name })
}

// Bắt lỗi unhandled Promise (API call, async onMounted, …)
if (globalThis.window !== undefined) {
  globalThis.addEventListener('unhandledrejection', (event) => {
    console.error('[UnhandledRejection]', event.reason)
  })
  globalThis.addEventListener('error', (event) => {
    console.error('[GlobalError]', event.error ?? event.message)
  })
}

const pinia = createPinia()
pinia.use(piniaPersistedState)
app.use(pinia)
app.use(router)
app.use(i18n)
app.use(VueQueryPlugin, { queryClient })
app.directive('permission', vPermission)

// Pre-fetch CSRF token so any POST after page load works without a retry round-trip.
// This covers the case where the user has an existing Frappe session (no login flow).
try {
  // Endpoint AssetCore (allow_guest) — Frappe vẫn set csrf_token cookie
  // mà không cần FE gọi trực tiếp vào frappe core API.
  const res = await axios.get<{ csrf_token?: string }>(
    '/api/method/assetcore.api.layout.ping_session',
    { withCredentials: true },
  )
  if (res.data?.csrf_token) setCsrfToken(res.data.csrf_token)
} catch {
  // not logged in yet — login flow will set the token
}

app.mount('#app')
