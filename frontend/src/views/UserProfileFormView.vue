<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getProfile, upsertProfile, getAvailableImmRoles } from '@/api/userProfile'
import type { ACUserProfile, ACUserRole, ACUserCertification } from '@/api/userProfile'

const props = defineProps<{ user?: string }>()
const router = useRouter()
const auth = useAuthStore()
const isEdit = computed(() => !!props.user)

const saving = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')
const isSynth = ref(false)   // 1 = profile chưa tồn tại, đang ở chế độ "tạo mới từ User"
const frappeRoles = ref<string[]>([])

const availableRoles = ref<Array<{ name: string; label: string }>>([])

// Quyền: chỉ IMM System Admin được sửa profile của user khác. User tự sửa profile của chính mình OK.
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

const newCert = ref<Partial<ACUserCertification>>({ cert_name: '', cert_number: '', issuer: '', issued_date: '', expiry_date: '' })

function hasRole(roleName: string): boolean {
  return (form.value.imm_roles ?? []).some(r => r.role === roleName)
}

function toggleRole(roleName: string) {
  const roles = form.value.imm_roles ?? []
  const idx = roles.findIndex(r => r.role === roleName)
  if (idx >= 0) {
    roles.splice(idx, 1)
  } else {
    roles.push({ role: roleName })
  }
  form.value.imm_roles = [...roles]
}

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

async function save() {
  if (!form.value.user?.trim()) { error.value = 'Vui lòng nhập User'; return }
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await upsertProfile(form.value)
    if (res) {
      success.value = 'Lưu thành công!'
      if (!isEdit.value) {
        router.push(`/user-profiles/${encodeURIComponent(res.user)}`)
      }
    }
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi khi lưu'
  } finally {
    saving.value = false
  }
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

    <div v-if="error" class="bg-red-50 text-red-700 text-sm p-3 rounded-lg">{{ error }}</div>
    <div v-if="success" class="bg-green-50 text-green-700 text-sm p-3 rounded-lg">{{ success }}</div>

    <!-- Banner: profile chưa tồn tại trong AssetCore -->
    <div v-if="!loading && isEdit && isSynth" class="bg-amber-50 border border-amber-200 text-amber-800 text-sm p-4 rounded-lg flex items-start gap-3">
      <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z" />
      </svg>
      <div>
        <p class="font-medium">User <code class="bg-amber-100 px-1 rounded">{{ props.user }}</code> chưa có hồ sơ AssetCore.</p>
        <p class="mt-1 text-xs">Đã pre-fill thông tin từ Frappe User. Điền đầy đủ và bấm <b>Lưu</b> để tạo hồ sơ AC User Profile mới.</p>
      </div>
    </div>

    <!-- Banner: read-only nếu không phải own profile + không phải admin -->
    <div v-if="!loading && isEdit && !canEdit" class="bg-slate-50 border border-slate-200 text-slate-700 text-sm p-3 rounded-lg">
      🔒 Bạn đang xem hồ sơ của người khác — chỉ <b>IMM System Admin</b> được phép sửa.
    </div>

    <form v-else-if="!loading" class="space-y-6" @submit.prevent="save">
      <!-- Basic Info -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Thông tin cơ bản</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">User (Frappe) <span class="text-red-500">*</span></label>
            <input
              v-model="form.user"
              type="text"
              :disabled="isEdit"
              placeholder="admin@example.com"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50 disabled:text-gray-500"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Mã nhân viên</label>
            <input
              v-model="form.employee_code"
              type="text"
              placeholder="NV001"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Chức danh</label>
            <input
              v-model="form.job_title"
              type="text"
              placeholder="KTV thiết bị y tế"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Điện thoại</label>
            <input
              v-model="form.phone"
              type="text"
              placeholder="0901234567"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Khoa / Phòng</label>
            <input
              v-model="form.department"
              type="text"
              placeholder="Khoa VTYT"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Vị trí làm việc</label>
            <input
              v-model="form.location"
              type="text"
              placeholder="Phòng kỹ thuật"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
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
        <p class="text-xs text-gray-500">Chọn các role IMM — sẽ được đồng bộ sang User.roles khi lưu.</p>
        <div class="grid grid-cols-2 gap-2">
          <label
            v-for="role in availableRoles"
            :key="role.name"
            class="flex items-center gap-2 cursor-pointer rounded-lg border px-3 py-2 text-sm transition-colors"
            :class="hasRole(role.name) ? 'border-blue-400 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'"
          >
            <input
              type="checkbox"
              :checked="hasRole(role.name)"
              :disabled="!auth.isSystemAdmin"
              class="rounded"
              @change="toggleRole(role.name)"
            />
            {{ role.name }}
          </label>
        </div>
      </div>

      <!-- Certifications -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Chứng chỉ KTV</h2>

        <div v-if="(form.certifications ?? []).length > 0" class="space-y-2">
          <div
            v-for="(cert, idx) in form.certifications"
            :key="idx"
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
          <input v-model="newCert.cert_name" type="text" placeholder="Tên chứng chỉ *" class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          <input v-model="newCert.cert_number" type="text" placeholder="Số chứng chỉ" class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          <input v-model="newCert.issuer" type="text" placeholder="Đơn vị cấp" class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          <input v-model="newCert.expiry_date" type="date" placeholder="Ngày hết hạn" class="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
          <div class="col-span-2">
            <button type="button" class="text-blue-600 hover:underline text-sm" @click="addCert">+ Thêm chứng chỉ</button>
          </div>
        </div>
      </div>

      <!-- Notes -->
      <div class="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Ghi chú</h2>
        <textarea
          v-model="form.notes"
          rows="3"
          placeholder="Ghi chú thêm..."
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <!-- Messages -->
      <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{{ error }}</div>
      <div v-if="success" class="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm">{{ success }}</div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="submit"
          :disabled="saving || !auth.isSystemAdmin"
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg text-sm font-medium"
        >
          {{ saving ? 'Đang lưu...' : 'Lưu hồ sơ' }}
        </button>
        <button type="button" class="px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-600 hover:bg-gray-50" @click="router.back()">
          Hủy
        </button>
      </div>
    </form>
  </div>
</template>
