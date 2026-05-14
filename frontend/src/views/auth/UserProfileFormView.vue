<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SmartSelect from '@/components/common/SmartSelect.vue'
import {
  getUserInfo, updateUserInfo, createSystemUser, approveRegistration,
  getAvailableImmRoles, listFrappeUsers,
  listRoleProfiles, assignRoleProfile,
} from '@/api/user'
import type {
  IMMUser, CreateUserPayload, FrappeUserItem, ImmRoleOption, RoleProfileOption,
} from '@/api/user'
import { ROLE_GROUP_LABEL, type RoleGroup } from '@/constants/roles'
import { useFormDraft } from '@/composables/useFormDraft'

const props = defineProps<{ user?: string }>()
const router = useRouter()
const auth = useAuthStore()
const isEdit = computed(() => !!props.user)

const saving = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')
const detail = ref<IMMUser | null>(null)
const availableRoles = ref<ImmRoleOption[]>([])
const roleProfiles = ref<RoleProfileOption[]>([])
const selectedRoleProfile = ref<string>('')
const applyingProfile = ref(false)

const currentRoleProfile = computed<RoleProfileOption | null>(
  () => roleProfiles.value.find(p => p.name === selectedRoleProfile.value) ?? null,
)

async function applyRoleProfile() {
  if (!props.user) return
  applyingProfile.value = true
  error.value = ''
  try {
    await assignRoleProfile(props.user, selectedRoleProfile.value)
    // Reload user để lấy roles đã sync từ profile
    await reloadUser()
    success.value = selectedRoleProfile.value
      ? `Đã áp dụng Role Profile "${selectedRoleProfile.value}"`
      : 'Đã bỏ Role Profile'
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi áp dụng Role Profile'
  } finally {
    applyingProfile.value = false
  }
}

async function reloadUser() {
  if (!props.user) return
  const d = await getUserInfo(props.user)
  if (d) {
    detail.value = d
    selectedRoleProfile.value = d.role_profile_name ?? ''
    editRoles.value = (d.imm_roles ?? []).map((r: unknown) =>
      ({ role: typeof r === 'object' ? (r as { role: string }).role : (r as string) }))
  }
}

// Role nhóm theo group để render UI rõ ràng
const groupedRoles = computed<Array<{ group: RoleGroup; label: string; items: ImmRoleOption[] }>>(() => {
  const buckets = new Map<string, ImmRoleOption[]>()
  for (const r of availableRoles.value) {
    const g = r.group || 'Other'
    if (!buckets.has(g)) buckets.set(g, [])
    buckets.get(g)!.push(r)
  }
  const order: RoleGroup[] = ['Governance', 'Department', 'Engineering', 'Support']
  const result: Array<{ group: RoleGroup; label: string; items: ImmRoleOption[] }> = []
  for (const g of order) {
    const items = buckets.get(g)
    if (items?.length) result.push({ group: g, label: ROLE_GROUP_LABEL[g], items })
  }
  // Gom nhóm còn sót (nếu BE trả group mới chưa biết)
  for (const [g, items] of buckets) {
    if (!order.includes(g as RoleGroup)) {
      result.push({ group: g as RoleGroup, label: g, items })
    }
  }
  return result
})

// ── Create mode toggle ─────────────────────────────────────────────────────
const createMode = ref<'new' | 'pick'>('new')

// ── Frappe User autocomplete (pick mode) ───────────────────────────────────
const userSearch = ref('')
const userSearchResults = ref<FrappeUserItem[]>([])
const userSearchLoading = ref(false)
const pickedUser = ref<FrappeUserItem | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(userSearch, (val) => {
  if (createMode.value !== 'pick') return
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    userSearchLoading.value = true
    userSearchResults.value = (await listFrappeUsers(val, 20)) ?? []
    userSearchLoading.value = false
  }, 300)
})

function pickUser(u: FrappeUserItem) {
  pickedUser.value = u
  userSearch.value = u.full_name || u.name
  userSearchResults.value = []
}

// ── New user form ──────────────────────────────────────────────────────────
const newUser = ref<CreateUserPayload>({
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  phone: '',
  send_welcome_email: false,
  ac_department: '',
  imm_roles: [],
})

// Form draft tắt hoàn toàn cho create-user form — email là trường unique,
// việc restore email cũ từ localStorage gây nhầm lẫn (user nghĩ đã nhập mới
// nhưng thực tế submit email cũ → 409 "đã tồn tại"). Trade-off: mất tính năng
// khôi phục khi tab crash, nhưng UX rõ ràng hơn nhiều.
const { clear: clearNewUserDraft } = useFormDraft('user-profile-create', newUser, {
  enabled: false,
  exclude: ['password'],
})

// Defensive: xóa draft cũ trong localStorage (nếu có từ phiên trước có draft enabled).
if (typeof localStorage !== 'undefined') {
  try { localStorage.removeItem('assetcore.draft.user-profile-create.v1') } catch { /* ignore */ }
}

// ── Pick/Edit shared state ─────────────────────────────────────────────────
const isSelf = computed(() => props.user === auth.user?.name)
const canEdit = computed(() => isSelf.value || auth.isSystemAdmin)

const editRoles = ref<Array<{ role: string }>>([])
const editFields = ref({ full_name: '', phone: '', ac_department: '' })

// ── Role helpers ───────────────────────────────────────────────────────────
function hasRole(roleName: string): boolean {
  return editRoles.value.some(r => r.role === roleName)
}

function hasNewRole(roleName: string): boolean {
  return (newUser.value.imm_roles ?? []).some(r => r.role === roleName)
}

function toggleRole(roleName: string) {
  const idx = editRoles.value.findIndex(r => r.role === roleName)
  if (idx >= 0) editRoles.value.splice(idx, 1)
  else editRoles.value.push({ role: roleName })
}

function toggleNewRole(roleName: string) {
  const roles = newUser.value.imm_roles ?? []
  const idx = roles.findIndex(r => r.role === roleName)
  if (idx >= 0) roles.splice(idx, 1)
  else roles.push({ role: roleName })
}

// ── Approve / reject ───────────────────────────────────────────────────────
async function doApprove() {
  if (!props.user) return
  saving.value = true; error.value = ''
  try {
    await approveRegistration(props.user, 'approve', editRoles.value)
    success.value = 'Đã duyệt tài khoản.'
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi duyệt'
  } finally { saving.value = false }
}

async function doReject() {
  if (!props.user) return
  const reason = prompt('Lý do từ chối:')
  if (!reason) return
  saving.value = true; error.value = ''
  try {
    await approveRegistration(props.user, 'reject', [], reason)
    success.value = 'Đã từ chối tài khoản.'
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi từ chối'
  } finally { saving.value = false }
}

// ── Save handlers ──────────────────────────────────────────────────────────
async function saveEdit() {
  saving.value = true; error.value = ''; success.value = ''
  try {
    await updateUserInfo(props.user!, {
      full_name: editFields.value.full_name,
      phone: editFields.value.phone,
      ac_department: editFields.value.ac_department,
      imm_roles: editRoles.value,
    })
    success.value = 'Lưu thành công!'
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi lưu'
  } finally { saving.value = false }
}

async function savePick() {
  if (!pickedUser.value) { error.value = 'Vui lòng chọn user'; return }
  saving.value = true; error.value = ''; success.value = ''
  try {
    await updateUserInfo(pickedUser.value.name, {
      ac_department: editFields.value.ac_department,
      imm_roles: editRoles.value,
    })
    router.push(`/user-profiles/${encodeURIComponent(pickedUser.value.name)}`)
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi lưu'
  } finally { saving.value = false }
}

/** Khi BE trả 409 với existing_user → cho phép FE hiển thị link "Xem user hiện có". */
const existingUserConflict = ref<string | null>(null)

async function saveNew() {
  // Chuẩn hóa email: trim + lowercase trước khi gửi để khớp BE normalization.
  // Cũng giúp tránh trường hợp user paste email có khoảng trắng hoặc CAPS LOCK.
  const normalizedEmail = (newUser.value.email || '').trim().toLowerCase()
  if (!normalizedEmail) { error.value = 'Vui lòng nhập email'; return }
  if (!newUser.value.first_name?.trim()) { error.value = 'Vui lòng nhập họ tên'; return }
  newUser.value.email = normalizedEmail

  saving.value = true; error.value = ''; success.value = ''; existingUserConflict.value = null
  // Diagnostic: log payload thực tế gửi đi (xóa khi đã ổn định)
  console.log('[create-user] sending payload:', { ...newUser.value, password: '***' })
  try {
    const res = await createSystemUser(newUser.value)
    console.log('[create-user] response:', res)
    if (res) {
      clearNewUserDraft()
      router.push(`/user-profiles/${encodeURIComponent(res.user)}`)
    }
  } catch (e: unknown) {
    console.error('[create-user] error:', e)
    const err = e as { message?: string; extra?: Record<string, unknown>; httpStatus?: number; code?: string }
    error.value = err.message || 'Lỗi khi tạo user'
    if (err.extra?.existing_user) {
      existingUserConflict.value = String(err.extra.existing_user)
    }
  } finally { saving.value = false }
}

function viewExistingUser() {
  if (existingUserConflict.value) {
    router.push(`/user-profiles/${encodeURIComponent(existingUserConflict.value)}`)
  }
}

function handleSubmit() {
  if (isEdit.value) return saveEdit()
  if (createMode.value === 'pick') return savePick()
  return saveNew()
}

// ── Load ───────────────────────────────────────────────────────────────────
async function load() {
  if (!isEdit.value || !props.user) return
  loading.value = true
  try {
    detail.value = await getUserInfo(props.user)
    const d = detail.value
    editFields.value = {
      full_name: d.full_name || '',
      phone: d.phone || '',
      ac_department: d.ac_department || '',
    }
    editRoles.value = (d.imm_roles ?? []).map((r: any) => ({ role: typeof r === 'object' ? r.role : r }));
    selectedRoleProfile.value = d.role_profile_name ?? ''
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không tải được hồ sơ'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const [roles, profiles] = await Promise.all([
    getAvailableImmRoles(),
    listRoleProfiles(),
  ])
  availableRoles.value = roles ?? []
  roleProfiles.value = profiles ?? []
  await load()
})
</script>

<template>
  <div class="page-container animate-fade-in space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <button class="text-gray-500 hover:text-gray-700" @click="router.push('/user-profiles')">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <h1 class="text-xl font-semibold text-gray-800">
        {{ isEdit ? 'Hồ sơ người dùng' : 'Thêm người dùng mới' }}
      </h1>
    </div>

    <div v-if="loading" class="text-center text-gray-400 py-12">Đang tải...</div>

    <div v-if="!canEdit && isEdit && !loading" class="bg-slate-50 border border-slate-200 text-slate-700 text-sm p-3 rounded-lg">
      Bạn đang xem hồ sơ của người khác — chỉ <b>IMM System Admin</b> được phép sửa.
    </div>

    <!-- CREATE MODE TOGGLE -->
    <div v-if="!isEdit" class="flex rounded-lg border overflow-hidden text-sm font-medium w-fit">
      <button
        :class="['px-4 py-2 transition-colors', createMode === 'new' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50']"
        @click="createMode = 'new'"
      >
Tạo tài khoản mới
</button>
      <button
        :class="['px-4 py-2 transition-colors', createMode === 'pick' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50']"
        @click="createMode = 'pick'"
      >
Gán IMM cho user sẵn có
</button>
    </div>

    <div v-if="error" class="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200 flex items-start justify-between gap-3">
      <span class="flex-1">{{ error }}</span>
      <button
        v-if="existingUserConflict"
        type="button"
        class="shrink-0 text-xs font-medium text-blue-600 hover:text-blue-800 underline"
        @click="viewExistingUser"
      >Xem user hiện có →</button>
    </div>
    <div v-if="success" class="bg-green-50 text-green-700 text-sm p-3 rounded-lg border border-green-200">{{ success }}</div>

    <!-- ─── FORM: TẠO USER MỚI ─────────────────────────────────────────── -->
    <form v-if="!isEdit && createMode === 'new'" class="space-y-6" @submit.prevent="handleSubmit">
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Tài khoản người dùng</h2>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label for="new-email" class="block text-xs font-medium text-gray-600 mb-1">Email <span class="text-red-500">*</span></label>
            <input
id="new-email" v-model="newUser.email" type="email" placeholder="ktv@hospital.vn"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-first-name" class="block text-xs font-medium text-gray-600 mb-1">Họ tên <span class="text-red-500">*</span></label>
            <input
id="new-first-name" v-model="newUser.first_name" type="text" placeholder="Nguyễn Văn"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-last-name" class="block text-xs font-medium text-gray-600 mb-1">Tên đệm / tên</label>
            <input
id="new-last-name" v-model="newUser.last_name" type="text" placeholder="A"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-password" class="block text-xs font-medium text-gray-600 mb-1">Mật khẩu ban đầu</label>
            <input
id="new-password" v-model="newUser.password" type="password" placeholder="(để trống = auto-generate)"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" autocomplete="new-password" />
          </div>
          <div>
            <label for="new-phone" class="block text-xs font-medium text-gray-600 mb-1">Điện thoại</label>
            <input
id="new-phone" v-model="newUser.phone" type="text" placeholder="0901234567"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div>
            <label for="new-dept" class="block text-xs font-medium text-gray-600 mb-1">Khoa / Phòng</label>
            <SmartSelect id="new-dept" v-model="newUser.ac_department" doctype="AC Department" placeholder="Chọn khoa/phòng..." />
          </div>
          <div class="col-span-2 flex items-center gap-2">
            <input id="send-welcome" v-model="newUser.send_welcome_email" type="checkbox" class="rounded" />
            <label for="send-welcome" class="text-sm text-gray-700">Gửi email chào mừng</label>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div class="flex items-baseline justify-between">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Phân quyền IMM</h2>
          <p class="text-xs text-gray-400">Tick vào vai trò để gán quyền truy cập</p>
        </div>
        <div v-for="bucket in groupedRoles" :key="bucket.group" class="space-y-2">
          <h3 class="text-[11px] font-bold text-gray-400 uppercase tracking-widest">{{ bucket.label }}</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <label
              v-for="role in bucket.items" :key="role.name"
              class="flex items-start gap-2.5 cursor-pointer rounded-lg border px-3 py-2.5 text-sm transition-colors"
              :class="hasNewRole(role.name) ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'"
            >
              <input type="checkbox" :checked="hasNewRole(role.name)" class="rounded mt-0.5 shrink-0" @change="toggleNewRole(role.name)" />
              <div class="min-w-0 flex-1">
                <div class="font-medium" :class="hasNewRole(role.name) ? 'text-blue-700' : 'text-gray-800'">
                  {{ role.label }}
                </div>
                <p class="text-[11px] text-gray-500 mt-0.5 leading-tight">{{ role.description }}</p>
              </div>
            </label>
          </div>
        </div>
      </div>

      <div class="flex gap-3">
        <button
type="submit" :disabled="saving"
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium">
          {{ saving ? 'Đang tạo...' : 'Tạo tài khoản' }}
        </button>
        <button type="button" class="px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50" @click="router.push('/user-profiles')">Hủy</button>
      </div>
    </form>

    <!-- ─── FORM: GÁN ROLE CHO USER SẴN CÓ ────────────────────────────── -->
    <form v-else-if="!isEdit && createMode === 'pick'" class="space-y-6" @submit.prevent="handleSubmit">
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Chọn Frappe User</h2>
        <div class="relative">
          <input
            v-model="userSearch" type="text" placeholder="Tìm email hoặc tên..."
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <div v-if="userSearchLoading" class="absolute right-3 top-2.5 text-gray-400 text-xs">Đang tìm...</div>
          <div v-if="userSearchResults.length" class="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-52 overflow-y-auto">
            <button
              v-for="u in userSearchResults" :key="u.name"
              type="button"
              class="w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 flex items-center gap-2"
              @click="pickUser(u)"
            >
              <span class="font-medium text-gray-800">{{ u.full_name || u.name }}</span>
              <span class="text-gray-400 text-xs">{{ u.name }}</span>
            </button>
          </div>
        </div>
        <div v-if="pickedUser" class="text-sm text-blue-700 bg-blue-50 px-3 py-2 rounded-lg">
          Đã chọn: <b>{{ pickedUser.full_name || pickedUser.name }}</b>
        </div>
        <div>
          <label for="pick-dept" class="block text-xs font-medium text-gray-600 mb-1">Khoa / Phòng</label>
          <SmartSelect id="pick-dept" v-model="editFields.ac_department" doctype="AC Department" placeholder="Chọn khoa/phòng..." />
        </div>
      </div>

      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div class="flex items-baseline justify-between">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Phân quyền IMM</h2>
          <p class="text-xs text-gray-400">Tick vào vai trò để gán quyền truy cập</p>
        </div>
        <div v-for="bucket in groupedRoles" :key="bucket.group" class="space-y-2">
          <h3 class="text-[11px] font-bold text-gray-400 uppercase tracking-widest">{{ bucket.label }}</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <label
              v-for="role in bucket.items" :key="role.name"
              class="flex items-start gap-2.5 cursor-pointer rounded-lg border px-3 py-2.5 text-sm transition-colors"
              :class="hasRole(role.name) ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'"
            >
              <input type="checkbox" :checked="hasRole(role.name)" class="rounded mt-0.5 shrink-0" @change="toggleRole(role.name)" />
              <div class="min-w-0 flex-1">
                <div class="font-medium" :class="hasRole(role.name) ? 'text-blue-700' : 'text-gray-800'">
                  {{ role.label }}
                </div>
                <p class="text-[11px] text-gray-500 mt-0.5 leading-tight">{{ role.description }}</p>
              </div>
            </label>
          </div>
        </div>
      </div>

      <div class="flex gap-3">
        <button
type="submit" :disabled="saving || !pickedUser"
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium">
          {{ saving ? 'Đang lưu...' : 'Lưu' }}
        </button>
        <button type="button" class="px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50" @click="router.push('/user-profiles')">Hủy</button>
      </div>
    </form>

    <!-- ─── EDIT HỒ SƠ ────────────────────────────────────────────────── -->
    <template v-else-if="isEdit && !loading && detail">
      <!-- Thông tin đọc-only từ Employee -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Thông tin tài khoản</h2>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><span class="text-gray-500">Email:</span> <b>{{ detail.email }}</b></div>
          <div>
            <span class="text-gray-500">Trạng thái:</span>
            <span
class="ml-1 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
              :class="{
                'bg-green-100 text-green-700': detail.imm_approval_status === 'Approved',
                'bg-amber-100 text-amber-700': detail.imm_approval_status === 'Pending',
                'bg-red-100 text-red-700': detail.imm_approval_status === 'Rejected',
              }">
              {{ detail.imm_approval_status === 'Approved' ? 'Đã duyệt' : detail.imm_approval_status === 'Pending' ? 'Chờ duyệt' : 'Từ chối' }}
            </span>
          </div>
          <div v-if="detail.designation"><span class="text-gray-500">Chức danh:</span> <b>{{ detail.designation }}</b></div>
          <div v-if="detail.hr_docname"><span class="text-gray-500">Mã NV:</span> <b>{{ detail.hr_docname }}</b></div>
        </div>
        <!-- Approval actions -->
        <div v-if="auth.isSystemAdmin && detail.imm_approval_status === 'Pending'" class="flex gap-2 pt-2">
          <button :disabled="saving" class="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-4 py-1.5 rounded-lg text-xs font-medium" @click="doApprove">Duyệt tài khoản</button>
          <button :disabled="saving" class="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white px-4 py-1.5 rounded-lg text-xs font-medium" @click="doReject">Từ chối</button>
        </div>
        <div v-if="detail.imm_rejection_reason" class="text-xs text-red-600 bg-red-50 px-3 py-2 rounded">
          Lý do từ chối: {{ detail.imm_rejection_reason }}
        </div>
      </div>

      <form v-if="canEdit" class="space-y-6" @submit.prevent="handleSubmit">
        <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Thông tin cơ bản</h2>
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <label for="edit-fullname" class="block text-xs font-medium text-gray-600 mb-1">Họ và tên</label>
              <input
id="edit-fullname" v-model="editFields.full_name" type="text"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label for="edit-phone" class="block text-xs font-medium text-gray-600 mb-1">Điện thoại</label>
              <input
id="edit-phone" v-model="editFields.phone" type="text" placeholder="0901234567"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
            <div>
              <label for="edit-dept" class="block text-xs font-medium text-gray-600 mb-1">Khoa / Phòng</label>
              <SmartSelect id="edit-dept" v-model="editFields.ac_department" doctype="AC Department" placeholder="Chọn khoa/phòng..." />
            </div>
          </div>
        </div>

        <!-- Role Profile (Frappe core) — pick 1 profile, auto-sync roles -->
        <div v-if="auth.isSystemAdmin" class="bg-white rounded-xl border border-blue-200 p-5 space-y-3">
          <div class="flex items-baseline justify-between">
            <h2 class="text-sm font-semibold text-blue-900 uppercase tracking-wide">Role Profile (persona)</h2>
            <p class="text-xs text-gray-400">Chọn 1 persona — Frappe tự đồng bộ roles</p>
          </div>
          <div class="flex items-stretch gap-2">
            <select
              v-model="selectedRoleProfile"
              :disabled="applyingProfile"
              class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white disabled:bg-gray-50"
            >
              <option value="">— Không áp dụng persona — quản lý role thủ công</option>
              <option v-for="p in roleProfiles" :key="p.name" :value="p.name">
                {{ p.label }}
              </option>
            </select>
            <button
              type="button"
              :disabled="applyingProfile || selectedRoleProfile === (detail?.role_profile_name ?? '')"
              class="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-sm font-medium"
              @click="applyRoleProfile"
            >
              {{ applyingProfile ? 'Đang áp dụng...' : 'Áp dụng' }}
            </button>
          </div>
          <div v-if="currentRoleProfile" class="flex flex-wrap gap-1.5 pt-1">
            <span class="text-[11px] text-gray-500">Profile này gán các role:</span>
            <span
              v-for="r in currentRoleProfile.roles" :key="r.name"
              class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-100 text-blue-700"
            >
              {{ r.label }}
            </span>
          </div>
        </div>

        <!-- IMM Roles (admin only) — fallback thủ công -->
        <div v-if="auth.isSystemAdmin" class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <div class="flex items-baseline justify-between">
            <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Phân quyền IMM (chi tiết)</h2>
            <p class="text-xs text-gray-400">Chỉnh thủ công nếu không dùng Role Profile</p>
          </div>
          <div v-for="bucket in groupedRoles" :key="bucket.group" class="space-y-2">
            <h3 class="text-[11px] font-bold text-gray-400 uppercase tracking-widest">{{ bucket.label }}</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <label
                v-for="role in bucket.items" :key="role.name"
                class="flex items-start gap-2.5 cursor-pointer rounded-lg border px-3 py-2.5 text-sm transition-colors"
                :class="hasRole(role.name) ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'"
              >
                <input type="checkbox" :checked="hasRole(role.name)" class="rounded mt-0.5 shrink-0" @change="toggleRole(role.name)" />
                <div class="min-w-0 flex-1">
                  <div class="font-medium" :class="hasRole(role.name) ? 'text-blue-700' : 'text-gray-800'">
                    {{ role.label }}
                  </div>
                  <p class="text-[11px] text-gray-500 mt-0.5 leading-tight">{{ role.description }}</p>
                </div>
              </label>
            </div>
          </div>
        </div>

        <div class="flex gap-3">
          <button
type="submit" :disabled="saving"
            class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium">
            {{ saving ? 'Đang lưu...' : 'Lưu hồ sơ' }}
          </button>
          <button type="button" class="px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50" @click="router.push('/user-profiles')">Hủy</button>
        </div>
      </form>
    </template>
  </div>
</template>
