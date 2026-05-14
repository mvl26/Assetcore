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
const showConfirm = ref(false)

const saving = ref(false)
const error = ref('')
const success = ref('')

const validations = computed(() => ({
  hasOld:    oldPassword.value.length > 0,
  newLong:   newPassword.value.length >= 8,
  match:     newPassword.value.length > 0 && newPassword.value === confirmPassword.value,
  different: newPassword.value.length > 0 && newPassword.value !== oldPassword.value,
}))

const canSubmit = computed(() => Object.values(validations.value).every(Boolean))

const hint = computed(() => {
  const v = validations.value
  if (!v.hasOld)    return 'Vui lòng nhập mật khẩu hiện tại.'
  if (!v.newLong)   return 'Mật khẩu mới phải có tối thiểu 8 ký tự.'
  if (!v.different) return 'Mật khẩu mới phải khác mật khẩu hiện tại.'
  if (!v.match)     return 'Mật khẩu xác nhận chưa khớp.'
  return ''
})

async function submit(): Promise<void> {
  if (!canSubmit.value || saving.value) return
  error.value = ''
  success.value = ''
  saving.value = true
  try {
    await changeMyPassword(oldPassword.value, newPassword.value)
    success.value = 'Đổi mật khẩu thành công. Bạn sẽ được đăng xuất.'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    setTimeout(() => { void auth.logout() }, 1500)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Lỗi đổi mật khẩu'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page-container max-w-xl mx-auto">
    <div class="flex items-center gap-3 mb-6">
      <button
        type="button"
        class="w-9 h-9 inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
        title="Quay lại hồ sơ"
        @click="router.push('/profile')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 18l-6-6 6-6" />
        </svg>
      </button>
      <h1 class="text-2xl font-bold text-slate-900">Đổi mật khẩu</h1>
    </div>

    <form
      class="card space-y-4"
      autocomplete="off"
      @submit.prevent="submit"
    >
      <p class="text-sm text-slate-500">
        Người dùng:
        <span class="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">
          {{ auth.user?.name }}
        </span>
      </p>

      <div v-if="error" class="alert-error">
        <span>{{ error }}</span>
      </div>
      <div v-if="success" class="alert-success">
        <span>{{ success }}</span>
      </div>

      <div class="form-group">
        <label class="form-label">Mật khẩu hiện tại</label>
        <div class="relative">
          <input
            v-model="oldPassword"
            :type="showOld ? 'text' : 'password'"
            class="form-input pr-16"
            autocomplete="current-password"
            :disabled="saving || !!success"
          />
          <button
            type="button"
            class="absolute inset-y-0 right-2 text-xs text-slate-500 hover:text-slate-700 px-2"
            tabindex="-1"
            @click="showOld = !showOld"
          >
            {{ showOld ? 'Ẩn' : 'Hiện' }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Mật khẩu mới <span class="text-slate-400 font-normal">(≥ 8 ký tự)</span></label>
        <div class="relative">
          <input
            v-model="newPassword"
            :type="showNew ? 'text' : 'password'"
            class="form-input pr-16"
            autocomplete="new-password"
            :disabled="saving || !!success"
          />
          <button
            type="button"
            class="absolute inset-y-0 right-2 text-xs text-slate-500 hover:text-slate-700 px-2"
            tabindex="-1"
            @click="showNew = !showNew"
          >
            {{ showNew ? 'Ẩn' : 'Hiện' }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Xác nhận mật khẩu mới</label>
        <div class="relative">
          <input
            v-model="confirmPassword"
            :type="showConfirm ? 'text' : 'password'"
            class="form-input pr-16"
            autocomplete="new-password"
            :disabled="saving || !!success"
          />
          <button
            type="button"
            class="absolute inset-y-0 right-2 text-xs text-slate-500 hover:text-slate-700 px-2"
            tabindex="-1"
            @click="showConfirm = !showConfirm"
          >
            {{ showConfirm ? 'Ẩn' : 'Hiện' }}
          </button>
        </div>
      </div>

      <p v-if="hint && !success" class="text-xs text-amber-600">{{ hint }}</p>

      <div class="flex items-center gap-2 pt-2">
        <button
          type="submit"
          class="btn-primary"
          :disabled="!canSubmit || saving || !!success"
        >
          {{ saving ? 'Đang cập nhật...' : 'Đổi mật khẩu' }}
        </button>
        <button
          type="button"
          class="btn-secondary"
          :disabled="saving"
          @click="router.push('/profile')"
        >
          Hủy
        </button>
      </div>
    </form>
  </div>
</template>
