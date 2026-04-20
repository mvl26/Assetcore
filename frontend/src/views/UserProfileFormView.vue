<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  getProfile, upsertProfile, createUser, getAvailableImmRoles, listFrappeUsers,
} from '@/api/userProfile'
import type { ACUserProfile, ACUserRole, ACUserCertification, CreateUserPayload, FrappeUserItem } from '@/api/userProfile'

const props = defineProps<{ user?: string }>()
const router = useRouter()
const auth = useAuthStore()
const isEdit = computed(() => !!props.user)

const saving = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')
const isSynth = ref(false)
const frappeRoles = ref<string[]>([])
const availableRoles = ref<Array<{ name: string; label: string }>>([])

// ── Autocomplete tìm Frappe User (chỉ dùng khi tạo mới theo mode "pick") ──
const createMode = ref<'new' | 'pick'>('new')
const userSearch = ref('')
const userSearchResults = ref<FrappeUserItem[]>([])
const userSearchLoading = ref(false)
let userSearchTimer: ReturnType<typeof setTimeout> | null = null

async function searchUsers(q: string) {
  userSearchLoading.value = true
  userSearchResults.value = (await listFrappeUsers(q, 20)) ?? []
  userSearchLoading.value = false
}

watch(userSearch, (val) => {
  if (createMode.value !== 'pick') return
  if (userSearchTimer) clearTimeout(userSearchTimer)
  userSearchTimer = setTimeout(() => searchUsers(val), 300)
})

function pickUser(u: FrappeUserItem) {
  form.value.user = u.name
  form.value = { ...form.value, user: u.name }
  userSearch.value = u.full_name || u.name
  userSearchResults.value = []
}

// ── New-user form ──────────────────────────────────────────────────────────
const newUser = ref<CreateUserPayload>({
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  send_welcome_email: false,
  employee_code: '',
  job_title: '',
  phone: '',
  department: '',
  location: '',
  notes: '',
  imm_roles: [],
  certifications: [],
})

// ── Edit-profile form ──────────────────────────────────────────────────────
const isSelf = computed(() => props.user === auth.user?.name)
const canEdit = computed(() => isSelf.value || auth.isSystemAdmin)

const form = ref<Partial<ACUserProfile>>({
  user: '',
  employee_code: '',
  job_title: '',
  phone: '',
  department: '',
  location: '',
  is_active: 1,
  notes: '',
  imm_roles: [],
  certifications: [],
})

const newCert = ref<Partial<ACUserCertification>>({
  cert_name: '', cert_number: '', issuer: '', issued_date: '', expiry_date: '',
})

// ── Role helpers ───────────────────────────────────────────────────────────
function hasRole(rolesList: ACUserRole[] | undefined, roleName: string): boolean {
  return (rolesList ?? []).some(r => r.role === roleName)
}

function toggleRole(rolesList: ACUserRole[], roleName: string): ACUserRole[] {
  const idx = rolesList.findIndex(r => r.role === roleName)
  if (idx >= 0) { rolesList.splice(idx, 1) } else { rolesList.push({ role: roleName }) }
  return [...rolesList]
}

function toggleEditRole(roleName: string) {
  form.value.imm_roles = toggleRole(form.value.imm_roles ?? [], roleName)
}

function toggleNewRole(roleName: string) {
  newUser.value.imm_roles = toggleRole(newUser.value.imm_roles ?? [], roleName)
}

// ── Certifications ─────────────────────────────────────────────────────────
function addCert() {
  if (!newCert.value.cert_name?.trim()) return
  form.value.certifications = [...(form.value.certifications ?? []), { ...newCert.value } as ACUserCertification]
  newCert.value = { cert_name: '', cert_number: '', issuer: '', issued_date: '', expiry_date: '' }
}

function removeCert(idx: number) {
  const certs = [...(form.value.certifications ?? [])]
  certs.splice(idx, 1)
  form.value.certifications = certs
}

// ── Save handlers ──────────────────────────────────────────────────────────
async function saveEdit() {
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await upsertProfile(form.value)
    if (res) success.value = 'Lưu thành công!'
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi lưu'
  } finally {
    saving.value = false
  }
}

async function savePick() {
  if (!form.value.user?.trim()) { error.value = 'Vui lòng chọn user'; return }
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await upsertProfile(form.value)
    if (res) router.push(`/user-profiles/${encodeURIComponent(res.user)}`)
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi lưu'
  } finally {
    saving.value = false
  }
}

async function saveNew() {
  if (!newUser.value.email?.trim()) { error.value = 'Vui lòng nhập email'; return }
  if (!newUser.value.first_name?.trim()) { error.value = 'Vui lòng nhập họ tên'; return }
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await createUser(newUser.value)
    if (res) router.push(`/user-profiles/${encodeURIComponent(res.user)}`)
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi tạo user'
  } finally {
    saving.value = false
  }
}

function handleSubmit() {
  if (isEdit.value) return saveEdit()
  if (createMode.value === 'pick') return savePick()
  return saveNew()
}

onMounted(async () => {
  availableRoles.value = (await getAvailableImmRoles()) ?? []
  if (isEdit.value && props.user) {
    loading.value = true
    try {
      const data = await getProfile(props.user)
      if (data) {
        isSynth.value = data.is_synth === 1
        frappeRoles.value = data.frappe_roles ?? []
        form.value = {
          ...data,
          imm_roles: (data.imm_roles ?? []) as ACUserRole[],
          certifications: (data.certifications ?? []) as ACUserCertification[],
        }
      }
    } catch (e: unknown) {
      error.value = (e as Error).message || 'Không tải được hồ sơ'
    } finally {
      loading.value = false
    }
  }
})
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <button class="text-gray-500 hover:text-gray-700" @click="router.back()">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <h1 class="text-xl font-semibold text-gray-800">
        {{ isEdit ? 'Hồ sơ người dùng' : 'Thêm người dùng mới' }}
      </h1>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>

    <!-- Banners (edit mode) -->
    <template v-if="!loading && isEdit">
      <div v-if="isSynth" class="bg-amber-50 border border-amber-200 text-amber-800 text-sm p-4 rounded-lg flex items-start gap-3">
        <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z" />
        </svg>
        <div>
          <p class="font-medium">User <code class="bg-amber-100 px-1 rounded">{{ props.user }}</code> chưa có hồ sơ AssetCore.</p>
          <p class="mt-1 text-xs">Pre-fill từ Frappe User. Điền đầy đủ và bấm <b>Lưu</b> để tạo.</p>
        </div>
      </div>
      <div v-if="!canEdit" class="bg-slate-50 border border-slate-200 text-slate-700 text-sm p-3 rounded-lg">
        Bạn đang xem hồ sơ của người khác — chỉ <b>IMM System Admin</b> được phép sửa.
      </div>
    </template>

    <!-- CREATE MODE TOGGLE (new only) -->
    <div v-if="!isEdit" class="flex rounded-lg border overflow-hidden text-sm font-medium w-fit">
      <button
        :class="['px-4 py-2 transition-colors', createMode === 'new' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50']"
        @click="createMode = 'new'"
      >Tạo tài khoản mới</button>
      <button
        :class="['px-4 py-2 transition-colors', createMode === 'pick' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50']"
        @click="createMode = 'pick'"
      >Tạo hồ sơ cho user sẵn có</button>
    </div>

    <div v-if="error" class="bg-red-50 text-red-700 text-sm p-3 rounded-lg">{{ error }}</div>
    <div v-if="success" class="bg-green-50 text-green-700 text-sm p-3 rounded-lg">{{ success }}</div>

    <!-- ─── FORM: TẠO USER MỚI ─────────────────────────────────────────── -->
    <form v-if="!isEdit && createMode === 'new'" class="space-y-6" @submit.prevent="handleSubmit">
      <!-- Tài khoản Frappe -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Tài khoản Frappe</h2>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label for="new-email" class="block text-xs font-medium text-gray-600 mb-1">Email <span class="text-red-500">*</span></label>
            <input id="new-email" v-model="newUser.email" type="email" placeholder="ktv@hospital.vn"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-first-name" class="block text-xs font-medium text-gray-600 mb-1">Họ tên <span class="text-red-500">*</span></label>
            <input id="new-first-name" v-model="newUser.first_name" type="text" placeholder="Nguyễn Văn"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-last-name" class="block text-xs font-medium text-gray-600 mb-1">Tên đệm / tên</label>
            <input id="new-last-name" v-model="newUser.last_name" type="text" placeholder="A"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-password" class="block text-xs font-medium text-gray-600 mb-1">Mật khẩu ban đầu</label>
            <input id="new-password" v-model="newUser.password" type="password" placeholder="(để trống = auto-generate)"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div class="flex items-center gap-2 mt-4">
            <input id="send-welcome" v-model="newUser.send_welcome_email" type="checkbox" class="rounded" />
            <label for="send-welcome" class="text-sm text-gray-700">Gửi email chào mừng</label>
          </div>
        </div>
      </div>

      <!-- Thông tin IMM -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Thông tin hồ sơ IMM</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="new-emp-code" class="block text-xs font-medium text-gray-600 mb-1">Mã nhân viên</label>
            <input id="new-emp-code" v-model="newUser.employee_code" type="text" placeholder="NV001"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-job-title" class="block text-xs font-medium text-gray-600 mb-1">Chức danh</label>
            <input id="new-job-title" v-model="newUser.job_title" type="text" placeholder="KTV thiết bị y tế"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-phone" class="block text-xs font-medium text-gray-600 mb-1">Điện thoại</label>
            <input id="new-phone" v-model="newUser.phone" type="text" placeholder="0901234567"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-dept" class="block text-xs font-medium text-gray-600 mb-1">Khoa / Phòng</label>
            <input id="new-dept" v-model="newUser.department" type="text" placeholder="Khoa VTYT"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
        </div>
      </div>

      <!-- Phân quyền IMM -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Phân quyền IMM</h2>
        <div class="grid grid-cols-2 gap-2">
          <label
            v-for="role in availableRoles"
            :key="role.name"
            class="flex items-center gap-2 cursor-pointer rounded-lg border px-3 py-2 text-sm transition-colors"
            :class="hasRole(newUser.imm_roles, role.name) ? 'border-blue-400 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'"
          >
            <input type="checkbox" :checked="hasRole(newUser.imm_roles, role.name)" class="rounded" @change="toggleNewRole(role.name)" />
            {{ role.name }}
          </label>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button type="submit" :disabled="saving"
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium">
          {{ saving ? 'Đang tạo...' : 'Tạo tài khoản' }}
        </button>
        <button type="button" class="px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50" @click="router.back()">Hủy</button>
      </div>
    </form>

    <!-- ─── FORM: TẠO HỒ SƠ CHO USER SẴN CÓ ──────────────────────────── -->
    <form v-else-if="!isEdit && createMode === 'pick'" class="space-y-6" @submit.prevent="handleSubmit">
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Chọn Frappe User</h2>
        <div class="relative">
          <input
            v-model="userSearch"
            type="text"
            placeholder="Tìm email hoặc tên..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <div v-if="userSearchResults.length" class="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-52 overflow-y-auto">
            <button
              v-for="u in userSearchResults"
              :key="u.name"
              type="button"
              :disabled="u.has_profile === 1"
              class="w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 flex items-center justify-between disabled:opacity-40 disabled:cursor-not-allowed"
              @click="pickUser(u)"
            >
              <div>
                <span class="font-medium text-gray-800">{{ u.full_name || u.name }}</span>
                <span class="text-gray-400 ml-2 text-xs">{{ u.name }}</span>
              </div>
              <span v-if="u.has_profile" class="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">Đã có hồ sơ</span>
            </button>
          </div>
          <div v-if="userSearchLoading" class="absolute right-3 top-2.5 text-gray-400 text-xs">Đang tìm...</div>
        </div>
        <div v-if="form.user" class="text-sm text-blue-700 bg-blue-50 px-3 py-2 rounded-lg">
          Đã chọn: <b>{{ form.user }}</b>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="pick-emp-code" class="block text-xs font-medium text-gray-600 mb-1">Mã nhân viên</label>
            <input id="pick-emp-code" v-model="form.employee_code" type="text" placeholder="NV001"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="pick-job-title" class="block text-xs font-medium text-gray-600 mb-1">Chức danh</label>
            <input id="pick-job-title" v-model="form.job_title" type="text" placeholder="KTV thiết bị y tế"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
        </div>
      </div>

      <!-- Phân quyền IMM -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Phân quyền IMM</h2>
        <div class="grid grid-cols-2 gap-2">
          <label
            v-for="role in availableRoles"
            :key="role.name"
            class="flex items-center gap-2 cursor-pointer rounded-lg border px-3 py-2 text-sm transition-colors"
            :class="hasRole(form.imm_roles, role.name) ? 'border-blue-400 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'"
          >
            <input type="checkbox" :checked="hasRole(form.imm_roles, role.name)" class="rounded" @change="toggleEditRole(role.name)" />
            {{ role.name }}
          </label>
        </div>
      </div>

      <div class="flex gap-3">
        <button type="submit" :disabled="saving || !form.user"
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium">
          {{ saving ? 'Đang lưu...' : 'Tạo hồ sơ' }}
        </button>
        <button type="button" class="px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50" @click="router.back()">Hủy</button>
      </div>
    </form>

    <!-- ─── FORM: EDIT HỒ SƠ ──────────────────────────────────────────── -->
    <div v-else-if="isEdit && !loading">
      <div v-if="!canEdit" class="text-sm text-gray-500 text-center py-8">Chỉ xem — không có quyền chỉnh sửa.</div>
      <form v-else class="space-y-6" @submit.prevent="handleSubmit">
        <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Thông tin cơ bản</h2>
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <label for="edit-user" class="block text-xs font-medium text-gray-600 mb-1">User (Frappe)</label>
              <input id="edit-user" :value="form.user" disabled
                class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500" />
            </div>
            <div>
              <label for="edit-emp-code" class="block text-xs font-medium text-gray-600 mb-1">Mã nhân viên</label>
              <input id="edit-emp-code" v-model="form.employee_code" type="text" placeholder="NV001"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label for="edit-job-title" class="block text-xs font-medium text-gray-600 mb-1">Chức danh</label>
              <input id="edit-job-title" v-model="form.job_title" type="text" placeholder="KTV thiết bị y tế"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label for="edit-phone" class="block text-xs font-medium text-gray-600 mb-1">Điện thoại</label>
              <input id="edit-phone" v-model="form.phone" type="text" placeholder="0901234567"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label for="edit-dept" class="block text-xs font-medium text-gray-600 mb-1">Khoa / Phòng</label>
              <input id="edit-dept" v-model="form.department" type="text" placeholder="Khoa VTYT"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label for="edit-location" class="block text-xs font-medium text-gray-600 mb-1">Vị trí làm việc</label>
              <input id="edit-location" v-model="form.location" type="text" placeholder="Phòng kỹ thuật"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>
          <div class="flex items-center gap-2">
            <input id="is_active" v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0" class="rounded" />
            <label for="is_active" class="text-sm text-gray-700">Đang hoạt động</label>
          </div>
        </div>

        <!-- IMM Roles -->
        <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Phân quyền IMM</h2>
          <div class="grid grid-cols-2 gap-2">
            <label
              v-for="role in availableRoles"
              :key="role.name"
              class="flex items-center gap-2 cursor-pointer rounded-lg border px-3 py-2 text-sm transition-colors"
              :class="hasRole(form.imm_roles, role.name) ? 'border-blue-400 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'"
            >
              <input type="checkbox" :checked="hasRole(form.imm_roles, role.name)"
                :disabled="!auth.isSystemAdmin" class="rounded" @change="toggleEditRole(role.name)" />
              {{ role.name }}
            </label>
          </div>
        </div>

        <!-- Certifications -->
        <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Chứng chỉ KTV</h2>
          <div v-if="(form.certifications ?? []).length > 0" class="space-y-2">
            <div
              v-for="(cert, idx) in form.certifications" :key="idx"
              class="flex items-center gap-3 bg-gray-50 rounded-lg px-3 py-2 text-sm"
            >
              <div class="flex-1">
                <span class="font-medium">{{ cert.cert_name }}</span>
                <span v-if="cert.cert_number" class="text-gray-500 ml-2">· {{ cert.cert_number }}</span>
                <span v-if="cert.issuer" class="text-gray-500 ml-2">· {{ cert.issuer }}</span>
                <span v-if="cert.expiry_date" class="text-gray-400 ml-2 text-xs">HH: {{ cert.expiry_date }}</span>
              </div>
              <button type="button" class="text-red-500 hover:text-red-700 text-xs" @click="removeCert(idx)">Xóa</button>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3 border-t border-gray-100 pt-4">
            <input v-model="newCert.cert_name" type="text" placeholder="Tên chứng chỉ *"
              class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            <input v-model="newCert.cert_number" type="text" placeholder="Số chứng chỉ"
              class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            <input v-model="newCert.issuer" type="text" placeholder="Đơn vị cấp"
              class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            <input v-model="newCert.expiry_date" type="date"
              class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            <div class="col-span-2">
              <button type="button" class="text-blue-600 hover:underline text-sm" @click="addCert">+ Thêm chứng chỉ</button>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Ghi chú</h2>
          <textarea v-model="form.notes" rows="3" placeholder="Ghi chú thêm..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>

        <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{{ error }}</div>
        <div v-if="success" class="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm">{{ success }}</div>

        <div class="flex gap-3">
          <button type="submit" :disabled="saving || !auth.isSystemAdmin"
            class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium">
            {{ saving ? 'Đang lưu...' : 'Lưu hồ sơ' }}
          </button>
          <button type="button" class="px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50" @click="router.back()">Hủy</button>
        </div>
      </form>
    </div>
  </div>
</template>
