<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUserProfile, updateMyProfile, changePassword, type UserProfileResult } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const data = ref<UserProfileResult | null>(null)
const loading = ref(false)
const err = ref('')
const ok = ref('')

const edit = ref({ full_name: '', phone: '', job_title: '', employee_code: '' })
const pw = ref({ old_password: '', new_password: '', confirm: '' })

async function load() {
  loading.value = true
  err.value = ''
  try {
    data.value = await getUserProfile()
    const p = data.value.profile
    if (p) {
      edit.value = {
        full_name: p.full_name || '',
        phone: p.phone || '',
        job_title: p.job_title || '',
        employee_code: p.employee_code || '',
      }
    }
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Lỗi tải hồ sơ'
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  err.value = ''; ok.value = ''
  try {
    await updateMyProfile(edit.value)
    ok.value = 'Đã cập nhật hồ sơ.'
    await load()
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Cập nhật thất bại'
  }
}

async function changePw() {
  err.value = ''; ok.value = ''
  if (pw.value.new_password.length < 8) { err.value = 'Mật khẩu mới phải từ 8 ký tự.'; return }
  if (pw.value.new_password !== pw.value.confirm) { err.value = 'Mật khẩu xác nhận không khớp.'; return }
  try {
    await changePassword(pw.value.old_password, pw.value.new_password)
    ok.value = 'Đổi mật khẩu thành công.'
    pw.value = { old_password: '', new_password: '', confirm: '' }
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Đổi mật khẩu thất bại'
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container max-w-3xl space-y-5">
    <h1 class="text-xl font-semibold text-slate-800">Hồ sơ của tôi</h1>

    <div v-if="err" class="alert-error text-sm">{{ err }}</div>
    <div v-if="ok" class="bg-green-50 border border-green-200 text-green-800 rounded-lg p-3 text-sm">{{ ok }}</div>

    <div v-if="loading" class="card p-8 text-center text-slate-400">Đang tải...</div>
    <template v-else-if="data">
      <!-- Thông tin cơ bản -->
      <div class="card p-5 space-y-3">
        <h2 class="font-medium text-slate-700">Thông tin tài khoản</h2>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><span class="text-slate-500">Email:</span> <b>{{ data.user.email }}</b></div>
          <div>
            <span class="text-slate-500">Trạng thái duyệt:</span>
            <b :class="data.profile?.approval_status === 'Approved' ? 'text-green-600' : 'text-amber-600'">
              {{ data.profile?.approval_status || '—' }}
            </b>
          </div>
          <div class="col-span-2">
            <span class="text-slate-500">Khoa / Phòng:</span> <b>{{ data.profile?.department_name || '—' }}</b>
          </div>
          <div class="col-span-2">
            <span class="text-slate-500">Roles:</span>
            <span v-for="r in data.roles" :key="r" class="inline-block bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs ml-1">{{ r }}</span>
            <span v-if="!data.roles.length" class="text-slate-400 text-xs ml-1">(chưa có role)</span>
          </div>
        </div>
      </div>

      <!-- Sửa thông tin cá nhân -->
      <div class="card p-5 space-y-3">
        <h2 class="font-medium text-slate-700">Cập nhật hồ sơ</h2>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="form-label">Họ và tên</label>
            <input v-model="edit.full_name" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Số điện thoại</label>
            <input v-model="edit.phone" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Chức danh</label>
            <input v-model="edit.job_title" class="form-input w-full" />
          </div>
          <div>
            <label class="form-label">Mã nhân viên</label>
            <input v-model="edit.employee_code" class="form-input w-full" />
          </div>
        </div>
        <div class="flex justify-end">
          <button class="btn-primary text-sm" @click="saveProfile">Lưu thay đổi</button>
        </div>
      </div>

      <!-- Đổi mật khẩu -->
      <div class="card p-5 space-y-3">
        <h2 class="font-medium text-slate-700">Đổi mật khẩu</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label class="form-label">Mật khẩu hiện tại</label>
            <input v-model="pw.old_password" type="password" class="form-input w-full" autocomplete="current-password" />
          </div>
          <div>
            <label class="form-label">Mật khẩu mới</label>
            <input v-model="pw.new_password" type="password" class="form-input w-full" autocomplete="new-password" />
          </div>
          <div>
            <label class="form-label">Xác nhận</label>
            <input v-model="pw.confirm" type="password" class="form-input w-full" autocomplete="new-password" />
          </div>
        </div>
        <div class="flex justify-end">
          <button class="btn-primary text-sm" @click="changePw">Đổi mật khẩu</button>
        </div>
      </div>

      <div class="flex justify-end">
        <button class="btn-ghost text-sm" @click="auth.logout()">Đăng xuất</button>
      </div>
    </template>
  </div>
</template>
