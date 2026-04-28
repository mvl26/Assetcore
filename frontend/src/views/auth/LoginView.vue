<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const remember = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  const prefill = auth.rememberedUsername()
  if (prefill) {
    email.value = prefill
    remember.value = true
  }
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
  const ok = await auth.login(email.value, password.value, remember.value)
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
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl mb-4 shadow-lg overflow-hidden">
          <img
:src="'/files/Screenshot%202025-01-25%20222056e16930.png'"
               alt="AssetCore"
               class="w-full h-full object-contain p-1" />
        </div>
        <h1 class="font-display text-2xl font-bold text-gray-900">AssetCore</h1>
        <p class="text-gray-500 mt-1 text-sm">Hệ thống Quản lý Thiết bị Y tế</p>
      </div>

      <div class="bg-white rounded-2xl shadow-xl p-8">
        <h2 class="font-display text-lg font-semibold text-gray-800 mb-6">Đăng nhập hệ thống</h2>

        <form class="space-y-5" @submit.prevent="handleLogin">
          <div v-if="error" class="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <svg class="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm text-red-700">{{ error }}</p>
          </div>

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

          <div>
            <label class="form-label" for="password">Mật khẩu</label>
            <div class="relative">
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input pr-10"
                placeholder="••••••••"
                autocomplete="current-password"
                :disabled="auth.loading"
              />
              <button
                type="button"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none"
                :title="showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18M10.584 10.587a2 2 0 002.828 2.83M9.363 5.365A9.466 9.466 0 0112 5c6.5 0 10 7 10 7a17.9 17.9 0 01-3.357 4.133M6.223 6.225A17.99 17.99 0 002 12s3.5 7 10 7a9.47 9.47 0 005.635-1.858" />
                </svg>
              </button>
            </div>
          </div>

          <label class="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
            <input
              v-model="remember"
              type="checkbox"
              class="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-400"
              :disabled="auth.loading"
            />
            <span>Nhớ tên đăng nhập</span>
          </label>

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

        <div class="mt-4 text-center text-sm text-gray-500">
          Chưa có tài khoản?
          <router-link to="/register" class="text-blue-600 font-medium hover:underline">Đăng ký</router-link>
        </div>

        <div class="mt-6 pt-6 border-t border-gray-100 text-center">
          <p class="text-xs text-gray-400">
            AssetCore — Hệ thống quản lý vòng đời thiết bị y tế (HTM)
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
