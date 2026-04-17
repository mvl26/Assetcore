// Copyright (c) 2026, AssetCore Team
// App bootstrap

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import axios from 'axios'
import { setCsrfToken } from '@/api/axios'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Pre-fetch CSRF token so any POST after page load works without a retry round-trip.
// This covers the case where the user has an existing Frappe session (no login flow).
try {
  const res = await axios.get<{ csrf_token?: string }>(
    '/api/method/frappe.auth.get_logged_user',
    { withCredentials: true },
  )
  if (res.data?.csrf_token) setCsrfToken(res.data.csrf_token)
} catch {
  // not logged in yet — login flow will set the token
}

app.mount('#app')
