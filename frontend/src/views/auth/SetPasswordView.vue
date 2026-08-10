<script setup lang="ts">
// ISS-002 — Màn hình tự đặt mật khẩu của AssetCore.
//
// Người dùng mới nhận email chào mừng → bấm "Đặt mật khẩu" → mở màn này với
// ?key=<key>. Thay thế form /update-password của Frappe desk (tiếng Anh, giao
// diện khác hệ thống). Không cần đăng nhập: 2 endpoint BE đều allow_guest,
// chính key trong link là bằng chứng sở hữu hộp thư.
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { verifyPasswordKey, setPasswordWithKey } from '@/api/auth'
import logoUrl from '@/assets/logo-miyano.png'

const MIN_LENGTH = 8

const route = useRoute()

const checking = ref(true)
const linkError = ref<string | null>(null)
const identity = ref<{ user: string; full_name: string; login_url: string } | null>(null)

const password = ref('')
const confirm = ref('')
const showPassword = ref(false)
const formError = ref<string | null>(null)
const submitting = ref(false)
const done = ref(false)
const doneMessage = ref('')
const loginUrl = ref('/login')

function messageOf(e: unknown, fallback: string): string {
  return e instanceof Error && e.message ? e.message : fallback
}

onMounted(async () => {
  const key = typeof route.query.key === 'string' ? route.query.key.trim() : ''
  if (!key) {
    checking.value = false
    linkError.value =
      'Liên kết đặt mật khẩu không hợp lệ. Vui lòng mở lại liên kết trong email, ' +
      'hoặc liên hệ quản trị viên để được cấp lại.'
    return
  }
  try {
    const res = await verifyPasswordKey(key)
    identity.value = res
    loginUrl.value = res.login_url || '/login'
  } catch (e) {
    linkError.value = messageOf(
      e,
      'Không kiểm tra được liên kết đặt mật khẩu. Vui lòng thử lại hoặc liên hệ quản trị viên.',
    )
  } finally {
    checking.value = false
  }
})

async function handleSubmit() {
  formError.value = null
  if (password.value.length < MIN_LENGTH) {
    formError.value = `Mật khẩu phải có tối thiểu ${MIN_LENGTH} ký tự.`
    return
  }
  if (password.value !== confirm.value) {
    formError.value = 'Mật khẩu nhập lại không khớp.'
    return
  }

  const key = typeof route.query.key === 'string' ? route.query.key.trim() : ''
  submitting.value = true
  try {
    const res = await setPasswordWithKey(key, password.value)
    doneMessage.value = res.message || 'Đặt mật khẩu thành công. Bạn có thể đăng nhập ngay.'
    loginUrl.value = res.login_url || loginUrl.value
    done.value = true
  } catch (e) {
    formError.value = messageOf(e, 'Không đặt được mật khẩu. Vui lòng thử lại.')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
<div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-20 h-20 bg-white rounded-2xl mb-4 shadow-lg overflow-hidden">
          <img :src="logoUrl" alt="AssetCore" class="w-full h-full object-contain p-2" />
        </div>
        <h1 class="font-display text-2xl font-bold text-gray-900">AssetCore</h1>
        <p class="text-gray-500 mt-1 text-sm">Hệ thống Quản lý Thiết bị Y tế</p>
      </div>

      <div class="bg-white rounded-2xl shadow-xl p-8">
<!-- 1. Đang kiểm tra liên kết -->
        <div v-if="checking" class="flex items-center gap-3 text-sm text-gray-600">
          <svg class="w-4 h-4 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Đang kiểm tra liên kết đặt mật khẩu...
        </div>

        <!-- 2. Liên kết hỏng / hết hạn / thiếu key -->
        <div v-else-if="linkError">
          <h2 class="font-display text-lg font-semibold text-gray-800 mb-4">Không mở được liên kết</h2>
          <div
role="alert" aria-live="assertive"
            class="flex items-start gap-2.5 p-3 rounded-lg border text-sm bg-amber-50 border-amber-200 text-amber-800">
            <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>{{ linkError }}</p>
          </div>
          <a
:href="loginUrl" data-test="go-login"
            class="btn-primary w-full justify-center py-2.5 mt-6 inline-flex">Về trang đăng nhập</a>
        </div>

        <!-- 3. Đặt xong -->
        <div v-else-if="done">
          <h2 class="font-display text-lg font-semibold text-gray-800 mb-4">Đã đặt mật khẩu</h2>
          <div
role="status" aria-live="polite"
            class="flex items-start gap-2.5 p-3 rounded-lg border text-sm bg-green-50 border-green-200 text-green-800">
            <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <p>{{ doneMessage }}</p>
          </div>
          <a
:href="loginUrl" data-test="go-login"
            class="btn-primary w-full justify-center py-2.5 mt-6 inline-flex">Đăng nhập ngay</a>
        </div>

        <!-- 4. Form đặt mật khẩu -->
        <div v-else>
          <h2 class="font-display text-lg font-semibold text-gray-800 mb-1">Đặt mật khẩu cho tài khoản</h2>
          <p class="text-sm text-gray-600 mb-6">
            Xin chào <b>{{ identity?.full_name }}</b>. Tên đăng nhập của bạn là
            <b>{{ identity?.user }}</b>. Hãy đặt mật khẩu để bắt đầu sử dụng hệ thống.
          </p>

          <form class="space-y-5" @submit.prevent="handleSubmit">
            <div
v-if="formError" role="alert" aria-live="assertive"
              class="flex items-start gap-2.5 p-3 rounded-lg border text-sm bg-red-50 border-red-200 text-red-700">
              <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>{{ formError }}</p>
            </div>

            <div>
              <label class="form-label" for="new-password">Mật khẩu mới</label>
              <div class="relative">
                <input
id="new-password" v-model="password" :type="showPassword ? 'text' : 'password'"
                  class="form-input pr-10" placeholder="••••••••" autocomplete="new-password"
                  :disabled="submitting" />
                <button
type="button"
                  class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none"
                  :title="showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'" @click="showPassword = !showPassword">
                  <svg v-if="!showPassword" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                    <path
stroke-linecap="round" stroke-linejoin="round"
                      d="M3 3l18 18M10.584 10.587a2 2 0 002.828 2.83M9.363 5.365A9.466 9.466 0 0112 5c6.5 0 10 7 10 7a17.9 17.9 0 01-3.357 4.133M6.223 6.225A17.99 17.99 0 002 12s3.5 7 10 7a9.47 9.47 0 005.635-1.858" />
                  </svg>
                </button>
              </div>
              <p class="text-xs text-gray-500 mt-1.5">
                Tối thiểu {{ MIN_LENGTH }} ký tự. Nên kết hợp chữ hoa, chữ thường, số và ký tự đặc biệt.
              </p>
            </div>

            <div>
              <label class="form-label" for="confirm-password">Nhập lại mật khẩu</label>
              <input
id="confirm-password" v-model="confirm" :type="showPassword ? 'text' : 'password'"
                class="form-input" placeholder="••••••••" autocomplete="new-password" :disabled="submitting" />
            </div>

            <button type="submit" class="btn-primary w-full justify-center py-2.5" :disabled="submitting">
              <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {{ submitting ? 'Đang lưu...' : 'Đặt mật khẩu' }}
            </button>
          </form>
        </div>
</div>

      <p class="text-center text-xs text-gray-500 mt-6">
        Cần hỗ trợ? Liên hệ quản trị viên hệ thống của đơn vị.
      </p>
    </div>
  </div>
</template>
