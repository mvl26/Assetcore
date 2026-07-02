<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { accountState } from '@/api/auth'
import { isSafeInternalRedirect } from '@/utils/navigation'
import logoUrl from '@/assets/logo-miyano.png'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// Open-redirect guard (ADR-001 D4): route.query.redirect là untrusted input từ
// luồng QR deep-link → 401 → login. Chỉ điều hướng tới path nội bộ hợp lệ; mọi
// giá trị độc hại (//evil, https://x, javascript:, \\evil) → fallback /dashboard.
// SSoT = isSafeInternalRedirect (utils/navigation). Dùng CHUNG cho cả 2 call site.
const safeRedirect = computed<string>(() => {
  const raw = route.query.redirect
  return isSafeInternalRedirect(raw) ? (raw as string) : '/dashboard'
})

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const remember = ref(false)
const error = ref<string | null>(null)
const errorType = ref<'credential' | 'network' | 'server' | 'validation' | 'pending' | 'rejected' | 'disabled' | null>(null)

onMounted(async () => {
  const prefill = auth.rememberedUsername()
  if (prefill) {
    email.value = prefill
    remember.value = true
  }
  if (auth.isAuthenticated) {
    router.push(safeRedirect.value)
  }
})

function classifyError(msg: string): typeof errorType.value {
  const m = msg.toLowerCase()
  if (m.includes('mật khẩu') || m.includes('password') || m.includes('incorrect') || m.includes('sai') || m.includes('unauthorized') || m.includes('invalid login')) return 'credential'
  if (m.includes('network') || m.includes('kết nối') || m.includes('connect') || m.includes('fetch') || m.includes('econnrefused')) return 'network'
  if (m.includes('500') || m.includes('server') || m.includes('máy chủ')) return 'server'
  return 'credential'
}

const ERROR_MESSAGES: Record<string, string> = {
  credential: 'Sai email hoặc mật khẩu. Vui lòng thử lại.',
  network:    'Không kết nối được máy chủ. Kiểm tra mạng và thử lại.',
  server:     'Máy chủ đang gặp sự cố. Vui lòng thử lại sau.',
  validation: 'Vui lòng nhập đầy đủ email và mật khẩu.',
  pending:    'Tài khoản của bạn đang chờ quản trị viên phê duyệt. Vui lòng thử lại sau khi được duyệt.',
  rejected:   'Đăng ký của bạn đã bị từ chối. Vui lòng liên hệ quản trị viên để biết thêm chi tiết.',
  disabled:   'Tài khoản của bạn đã bị vô hiệu hoá. Vui lòng liên hệ quản trị viên.',
}

const ERROR_BANNER_CLASS = computed<string>(() => {
  if (errorType.value === 'network') return 'bg-amber-50 border-amber-200 text-amber-800'
  if (errorType.value === 'server')  return 'bg-orange-50 border-orange-200 text-orange-800'
  // pending/rejected/disabled = trạng thái tài khoản (không phải sai credential) → amber
  if (errorType.value === 'pending' || errorType.value === 'rejected' || errorType.value === 'disabled')
    return 'bg-amber-50 border-amber-200 text-amber-800'
  return 'bg-red-50 border-red-200 text-red-700'
})

async function handleLogin() {
  if (!email.value.trim() || !password.value) {
    errorType.value = 'validation'
    error.value = ERROR_MESSAGES.validation
    return
  }
  error.value = null
  errorType.value = null
  const ok = await auth.login(email.value.trim(), password.value, remember.value)
  if (ok) {
    router.push(safeRedirect.value)
    return
  }

  // Login fail: phân biệt nguyên nhân trạng thái tài khoản (chờ duyệt / bị từ
  // chối / vô hiệu hoá) vs sai mật khẩu. BR-00-USR-02 (security): gọi endpoint
  // PASSWORD-GATED account_state với CHÍNH mật khẩu user vừa nhập — BE chỉ lộ
  // pending/rejected/disabled SAU KHI mật khẩu đúng (không enumeration).
  // Best-effort: nếu lookup lỗi → fallback về classify theo message gốc.
  const raw = auth.error ?? ''
  try {
    const { status } = await accountState(email.value.trim(), password.value)
    if (status === 'pending' || status === 'rejected' || status === 'disabled') {
      errorType.value = status
      error.value = ERROR_MESSAGES[status]
      return
    }
    // 'active' (mật khẩu đúng nhưng login fail vì lý do khác) hoặc
    // 'invalid_credentials' (sai email/mật khẩu) → message credential trung lập,
    // KHÔNG khẳng định email tồn tại hay không.
    errorType.value = 'credential'
    error.value = ERROR_MESSAGES.credential
  } catch (e) {
    // accountState() ném (mạng/máy chủ/lỗi gọi endpoint) → KHÔNG nuốt lỗi, KHÔNG
    // để form đứng im. Phân loại theo thông điệp lỗi của CHÍNH lần gọi vừa ném
    // trước, rồi mới fallback về error gốc của store (raw). Luôn đảm bảo có 1
    // message hiển thị (banner v-if=error render).
    const thrown = e instanceof Error ? e.message : ''
    errorType.value = classifyError(thrown || raw)
    error.value = ERROR_MESSAGES[errorType.value ?? ''] || raw || 'Đăng nhập thất bại. Vui lòng thử lại.'
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="w-full max-w-md">

      <!-- Logo + title -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-20 h-20 bg-white rounded-2xl mb-4 shadow-lg overflow-hidden">
          <img :src="logoUrl" alt="AssetCore" class="w-full h-full object-contain p-2" />
        </div>
        <h1 class="font-display text-2xl font-bold text-gray-900">AssetCore</h1>
        <p class="text-gray-500 mt-1 text-sm">Hệ thống Quản lý Thiết bị Y tế</p>
      </div>

      <div class="bg-white rounded-2xl shadow-xl p-8">
        <h2 class="font-display text-lg font-semibold text-gray-800 mb-6">Đăng nhập hệ thống</h2>

        <form class="space-y-5" @submit.prevent="handleLogin">

          <!-- Error banner — style theo loại lỗi. role=alert + aria-live=assertive
               để screen-reader đọc ngay khi login fail (FR-00 a11y). -->
          <div v-if="error" role="alert" aria-live="assertive"
            :class="['flex items-start gap-2.5 p-3 rounded-lg border text-sm', ERROR_BANNER_CLASS]">
            <!-- credential / validation / account-state (pending/rejected/disabled) -->
            <svg v-if="!errorType || errorType === 'credential' || errorType === 'validation' || errorType === 'pending' || errorType === 'rejected' || errorType === 'disabled'"
              class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <!-- network -->
            <svg v-else-if="errorType === 'network'"
              class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M18.364 5.636a9 9 0 010 12.728M15.536 8.464a5 5 0 010 7.072M3 3l18 18M8.464 8.464A5 5 0 006 12m2.343 5.657A5 5 0 0012 19.07" />
            </svg>
            <!-- server -->
            <svg v-else
              class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
            </svg>
            <p>{{ error }}</p>
          </div>

          <div>
            <label class="form-label" for="login-email">Email / Tên đăng nhập</label>
            <input
              id="login-email"
              v-model="email"
              type="email"
              class="form-input"
              :class="{ 'border-red-400 focus:ring-red-400': errorType === 'credential' }"
              placeholder="admin@hospital.vn"
              autocomplete="email"
              :disabled="auth.loading"
            />
          </div>

          <div>
            <label class="form-label" for="login-password">Mật khẩu</label>
            <div class="relative">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input pr-10"
                :class="{ 'border-red-400 focus:ring-red-400': errorType === 'credential' }"
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
          <p class="text-xs text-gray-400">AssetCore — Hệ thống quản lý vòng đời thiết bị y tế</p>
        </div>
      </div>
    </div>
  </div>
</template>
