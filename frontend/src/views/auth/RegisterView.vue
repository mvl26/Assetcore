<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { registerUser } from '@/api/auth'
import SmartSelect from '@/components/common/SmartSelect.vue'

const router = useRouter()

const form = ref({
  email: '',
  full_name: '',
  password: '',
  password_confirm: '',
  phone: '',
  department: '',
  employee_code: '',
  job_title: '',
})

const submitting = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

onMounted(() => {
  document.title = 'Đăng ký tài khoản — AssetCore'
})

function validate(): string | null {
  if (!form.value.email.trim()) return 'Vui lòng nhập email.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) return 'Email không hợp lệ.'
  if (!form.value.full_name.trim()) return 'Vui lòng nhập họ và tên.'
  if (form.value.password.length < 8) return 'Mật khẩu phải từ 8 ký tự.'
  if (form.value.password !== form.value.password_confirm) return 'Mật khẩu xác nhận không khớp.'
  return null
}

async function handleSubmit() {
  error.value = null
  success.value = null
  const v = validate()
  if (v) { error.value = v; return }

  submitting.value = true
  try {
    const res = await registerUser({
      email: form.value.email.trim(),
      full_name: form.value.full_name.trim(),
      password: form.value.password,
      phone: form.value.phone.trim(),
      department: form.value.department,
      employee_code: form.value.employee_code.trim(),
      job_title: form.value.job_title.trim(),
    })
    success.value = res.message
    setTimeout(() => router.push('/login'), 3000)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Đăng ký thất bại.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="w-full max-w-lg">
      <div class="text-center mb-6">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4 shadow-lg">
          <span class="font-display text-white font-bold text-2xl">AC</span>
        </div>
        <h1 class="text-2xl font-semibold text-slate-800">Đăng ký tài khoản AssetCore</h1>
        <p class="text-sm text-slate-500 mt-1">Tài khoản sẽ cần quản trị viên duyệt trước khi sử dụng.</p>
      </div>

      <div class="bg-white rounded-2xl shadow-xl p-6 space-y-4">
        <div v-if="error" class="alert-error text-sm">{{ error }}</div>
        <div v-if="success" class="bg-green-50 border border-green-200 text-green-800 rounded-lg p-3 text-sm">
          {{ success }} Đang chuyển về trang đăng nhập…
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div class="md:col-span-2">
            <label class="form-label">Email <span class="text-red-500">*</span></label>
            <input v-model="form.email" type="email" class="form-input w-full" placeholder="ten@bv.vn" autocomplete="username" />
          </div>
          <div class="md:col-span-2">
            <label class="form-label">Họ và tên <span class="text-red-500">*</span></label>
            <input v-model="form.full_name" type="text" class="form-input w-full" placeholder="Nguyễn Văn A" />
          </div>
          <div>
            <label class="form-label">Mật khẩu <span class="text-red-500">*</span></label>
            <input v-model="form.password" type="password" class="form-input w-full" autocomplete="new-password" />
            <p class="text-xs text-slate-400 mt-1">Tối thiểu 8 ký tự.</p>
          </div>
          <div>
            <label class="form-label">Xác nhận mật khẩu <span class="text-red-500">*</span></label>
            <input v-model="form.password_confirm" type="password" class="form-input w-full" autocomplete="new-password" />
          </div>
          <div>
            <label class="form-label">Số điện thoại</label>
            <input v-model="form.phone" type="tel" class="form-input w-full" placeholder="0912 345 678" />
          </div>
          <div>
            <label class="form-label">Mã nhân viên</label>
            <input v-model="form.employee_code" type="text" class="form-input w-full" placeholder="NV-0123" />
          </div>
          <div class="md:col-span-2">
            <label class="form-label">Khoa / Phòng công tác</label>
            <SmartSelect v-model="form.department" doctype="AC Department" placeholder="Chọn khoa/phòng..." />
          </div>
          <div class="md:col-span-2">
            <label class="form-label">Chức danh</label>
            <input v-model="form.job_title" type="text" class="form-input w-full" placeholder="Bác sĩ / Kỹ thuật viên / Điều dưỡng ..." />
          </div>
        </div>

        <button
          class="btn-primary w-full mt-2"
          :disabled="submitting || success !== null"
          @click="handleSubmit"
        >
          {{ submitting ? 'Đang gửi...' : 'Đăng ký' }}
        </button>

        <div class="text-center text-sm text-slate-500 pt-2">
          Đã có tài khoản?
          <router-link to="/login" class="text-blue-600 font-medium hover:underline">Đăng nhập</router-link>
        </div>
      </div>
    </div>
  </div>
</template>
