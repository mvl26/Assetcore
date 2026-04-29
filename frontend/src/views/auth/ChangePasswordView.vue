<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { changeMyPassword } from '@/api/user'

const router = useRouter()
const auth = useAuthStore()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showOld = ref(false)
const showNew = ref(false)

const saving = ref(false)
const error = ref('')
const success = ref('')

const canSubmit = computed(() =>
  !!oldPassword.value && newPassword.value.length >= 8
  && newPassword.value === confirmPassword.value
  && newPassword.value !== oldPassword.value,
)

async function submit(): Promise<void> {
  error.value = ''
  success.value = ''
  if (!canSubmit.value) return
  saving.value = true
  try {
    await changeMyPassword(oldPassword.value, newPassword.value)
    success.value = 'Đổi mật khẩu thành công. Bạn sẽ được đăng xuất.'
    setTimeout(() => { void auth.logout() }, 1500)
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi đổi mật khẩu'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="p-6 max-w-md mx-auto space-y-5">
    <div class="flex items-center gap-3">
      <button class="text-gray-500 hover:text-gray-700" @click="router.push('/profile')">←</button>
      <h1 class="text-xl font-semibold text-gray-800">Đổi mật khẩu</h1>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <p class="text-sm text-gray-500">
        Người dùng: <span class="font-mono text-gray-800">{{ auth.user?.name }}</span>
      </p>

      <div v-if="error" class="bg-red-50 text-red-700 text-sm p-3 rounded-lg">{{ error }}</div>
      <div v-if="success" class="bg-green-50 text-green-700 text-sm p-3 rounded-lg">{{ success }}</div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Mật khẩu hiện tại</label>
        <div class="relative">
          <input
            v-model="oldPassword"
            :type="showOld ? 'text' : 'password'"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            autocomplete="current-password"
          />
          <button
type="button" class="absolute inset-y-0 right-2 text-xs text-gray-500"
                  @click="showOld = !showOld">
{{ showOld ? 'Ẩn' : 'Hiện' }}
</button>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Mật khẩu mới (≥ 8 ký tự)</label>
        <div class="relative">
          <input
            v-model="newPassword"
            :type="showNew ? 'text' : 'password'"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            autocomplete="new-password"
          />
          <button
type="button" class="absolute inset-y-0 right-2 text-xs text-gray-500"
                  @click="showNew = !showNew">
{{ showNew ? 'Ẩn' : 'Hiện' }}
</button>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Xác nhận mật khẩu mới</label>
        <input
          v-model="confirmPassword"
          :type="showNew ? 'text' : 'password'"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          autocomplete="new-password"
        />
        <p
v-if="confirmPassword && newPassword !== confirmPassword"
           class="text-xs text-red-600 mt-1">
Mật khẩu xác nhận không khớp.
</p>
      </div>

      <button
        :disabled="!canSubmit || saving"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white py-2.5 rounded-lg text-sm font-medium"
        @click="submit"
      >
        {{ saving ? 'Đang cập nhật...' : 'Đổi mật khẩu' }}
      </button>
    </div>
  </div>
</template>
