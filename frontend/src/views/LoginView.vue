<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)

onMounted(async () => {
  if (auth.isAuthenticated) {
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  }
})

async function handleLogin() {
  if (!email.value || !password.value) {
    error.value = 'Vui lòng nhập email và mật khẩu.'
    return
  }

  error.value = null

  const ok = await auth.login(email.value, password.value)
  if (ok) {
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } else {
    error.value = auth.error ?? 'Đăng nhập thất bại. Vui lòng kiểm tra lại.'
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <!-- Logo card -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4 shadow-lg">
          <span class="text-white font-bold text-2xl">AC</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">AssetCore</h1>
        <p class="text-gray-500 mt-1 text-sm">Hệ thống Quản lý Thiết bị Y tế</p>
      </div>

      <!-- Login form -->
      <div class="bg-white rounded-2xl shadow-xl p-8">
        <h2 class="text-lg font-semibold text-gray-800 mb-6">Đăng nhập hệ thống</h2>

        <form class="space-y-5" @submit.prevent="handleLogin">
          <!-- Error -->
          <div v-if="error" class="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <svg class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm text-red-700">{{ error }}</p>
          </div>

          <!-- Email -->
          <div>
            <label class="form-label" for="email">Email / Tên đăng nhập</label>
            <input
              id="email"
              v-model="email"
              type="email"
              class="form-input"
              placeholder="admin@hospital.vn"
              autocomplete="username"
              :disabled="auth.loading"
            />
          </div>

          <!-- Password -->
          <div>
            <label class="form-label" for="password">Mật khẩu</label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="form-input"
              placeholder="••••••••"
              autocomplete="current-password"
              :disabled="auth.loading"
            />
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="btn-primary w-full justify-center py-2.5"
            :disabled="auth.loading"
          >
            <svg v-if="auth.loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {{ auth.loading ? 'Đang đăng nhập...' : 'Đăng nhập' }}
          </button>
        </form>

        <!-- Footer info -->
        <div class="mt-6 pt-6 border-t border-gray-100 text-center">
          <p class="text-xs text-gray-400">
            AssetCore IMM-04 — Module Đưa vào sử dụng Thiết bị Y tế
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
