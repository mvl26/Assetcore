<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { getUsersByRole } from '@/api/imm04'
import { listAssignableUsers, normalizeAssignableUserPage } from '@/api/user'
import type { AssignableUserPage } from '@/api/user'

// ─── Props & Emits ────────────────────────────────────────────────────────────

// Picker user typeahead, 2 nguồn (chọn 1):
//   - role:    user giữ 1 Frappe role cụ thể (commissioning approver — getUsersByRole).
//   - context: user AssetCore ĐỦ NĂNG LỰC cho ngữ cảnh phân công, lọc theo
//              capability/DocPerm (vd "repair" — listAssignableUsers). Ưu tiên khi set.
interface Props {
  modelValue: string | undefined | null
  role?: string
  context?: string
  label?: string
  placeholder?: string
  disabled?: boolean
  required?: boolean
  /** HTML id cho input bên trong — để <label for="..."> liên kết đúng. */
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  role: '',
  context: '',
  label: '',
  placeholder: 'Tìm theo tên hoặc email...',
  disabled: false,
  required: false,
  id: '',
})

/**
 * Nguồn user: context (capability) ưu tiên hơn role. Cả 2 nhánh trả cùng một
 * hình dạng `AssignableUserPage` để chỗ hiển thị chỉ đọc 1 kiểu.
 *
 * Nhánh `role=` (IMM-04 `get_users_by_role`) CHƯA công bố meta cắt ⇒ bọc
 * `truncated: 0` (vẫn cắt im lặng — backlog ADR-IMM00-TRUNCATION-SSOT §7.5).
 */
async function fetchUsers(q: string, limit: number): Promise<AssignableUserPage> {
  const rows = props.context
    ? await listAssignableUsers(props.context, q, limit)
    : await getUsersByRole(props.role, q, limit)
  // Chuẩn hoá lần nữa: rẻ, idempotent, và giữ picker sống nếu BE (hoặc test
  // giả lập) còn trả mảng trần theo hợp đồng cũ.
  return normalizeAssignableUserPage(rows, limit)
}

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// ─── State ────────────────────────────────────────────────────────────────────

interface UserOption {
  name: string
  /** null trên tài khoản cũ → hiển thị fallback về `name`. */
  full_name: string | null
  email: string | null
  user_image?: string | null
}

const query       = ref('')
const results     = ref<UserOption[]>([])
const loading     = ref(false)
const open        = ref(false)
const highlighted = ref(-1)
const selectedUser = ref<UserOption | null>(null)
/** Meta cắt (AC-CR-80): tổng người được phép + cờ đã cắt ở `limit`. */
const total       = ref(0)
const truncated   = ref<0 | 1>(0)

/** Nhãn hiển thị: KHÔNG bao giờ để trống ô tên khi `full_name` null. */
function displayName(u: UserOption): string {
  return u.full_name || u.name
}

// ─── Debounce search ──────────────────────────────────────────────────────────

let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function doSearch(q: string) {
  loading.value = true
  try {
    const page = await fetchUsers(q, 20)
    results.value = page.items
    total.value = page.total
    truncated.value = page.truncated
  } catch {
    // Lỗi tải: không có số liệu ⇒ KHÔNG khẳng định "đang hiển thị N/M".
    results.value = []
    total.value = 0
    truncated.value = 0
  } finally {
    loading.value = false
  }
}

function onInput(e: Event) {
  query.value = (e.target as HTMLInputElement).value
  highlighted.value = -1
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => doSearch(query.value), 250)
  open.value = true
}

// ─── Keyboard navigation ──────────────────────────────────────────────────────

function onKeydown(e: KeyboardEvent) {
  if (!open.value) {
    if (e.key === 'ArrowDown' || e.key === 'Enter') {
      open.value = true
      doSearch(query.value)
    }
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    highlighted.value = Math.min(highlighted.value + 1, results.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    highlighted.value = Math.max(highlighted.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (highlighted.value >= 0 && results.value[highlighted.value]) {
      selectUser(results.value[highlighted.value])
    }
  } else if (e.key === 'Escape') {
    open.value = false
  }
}

// ─── Selection ────────────────────────────────────────────────────────────────

function selectUser(user: UserOption) {
  selectedUser.value = user
  emit('update:modelValue', user.name)
  open.value = false
  query.value = ''
}

function clearSelection() {
  selectedUser.value = null
  emit('update:modelValue', '')
  query.value = ''
  open.value = false
}

function onFocus() {
  if (!selectedUser.value) {
    open.value = true
    doSearch(query.value)
  }
}

function onBlur() {
  // Small delay so @mousedown.prevent on items works
  setTimeout(() => { open.value = false }, 150)
}

// ─── Load user details when modelValue is pre-set ────────────────────────────

async function loadInitialUser(username: string) {
  if (!username) return
  // First try to find in a short search for their own name
  try {
    const page = await fetchUsers('', 50)
    const found = page.items.find(r => r.name === username)
    if (found) {
      selectedUser.value = found
    } else {
      // Fallback: show a simplified chip with just the username
      selectedUser.value = { name: username, full_name: username, email: username }
    }
  } catch {
    selectedUser.value = { name: username, full_name: username, email: username }
  }
}

onMounted(() => {
  if (props.modelValue) {
    loadInitialUser(props.modelValue)
  }
})

// Sync when modelValue changes externally
watch(() => props.modelValue, (val) => {
  if (!val) {
    selectedUser.value = null
  } else if (!selectedUser.value || selectedUser.value.name !== val) {
    loadInitialUser(val)
  }
})
</script>

<template>
  <div class="form-row">
    <label v-if="label" class="form-label">
      {{ label }}
      <span v-if="required" class="text-red-500 ml-0.5">*</span>
    </label>

    <div class="relative">
      <!-- Chip when user is selected -->
      <div
        v-if="selectedUser"
        class="flex items-start gap-2 px-2.5 py-2 bg-slate-50 rounded-lg border border-slate-200"
      >
        <!-- Avatar -->
        <img
          v-if="selectedUser.user_image"
          :src="selectedUser.user_image"
          class="w-7 h-7 rounded-full object-cover shrink-0 mt-0.5"
          :alt="displayName(selectedUser)"
        />
        <div
          v-else
          class="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
        >
          {{ displayName(selectedUser).charAt(0).toUpperCase() }}
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-800 truncate">{{ displayName(selectedUser) }}</p>
          <p class="text-xs text-slate-500 truncate">{{ selectedUser.email || selectedUser.name }}</p>
        </div>

        <!-- Clear button -->
        <button
          v-if="!disabled"
          type="button"
          class="shrink-0 text-slate-400 hover:text-red-500 transition-colors mt-0.5"
          aria-label="Xóa lựa chọn"
          @click="clearSelection"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Search input when no user selected -->
      <template v-else>
        <input
          :id="id || undefined"
          type="text"
          :value="query"
          :disabled="disabled"
          :placeholder="placeholder"
          class="form-input w-full text-sm pr-8"
          autocomplete="off"
          @input="onInput"
          @focus="onFocus"
          @blur="onBlur"
          @keydown="onKeydown"
        />
        <!-- Search icon -->
        <span class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
          <svg v-if="!loading" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7 7 0 1110 3a7 7 0 016.65 13.65z" />
          </svg>
          <svg v-else class="w-4 h-4 animate-spin text-brand-500" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
        </span>

        <!-- Dropdown -->
        <Transition
          enter-active-class="transition duration-150 ease-out"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <div
            v-if="open"
            class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden z-20"
          >
            <!--
              Vùng CUỘN chỉ bọc danh sách. Dải cảnh báo nằm NGOÀI vùng cuộn: để
              trong thì nó nằm sau 20 dòng, người dùng phải cuộn hết mới thấy —
              tức vẫn là "cắt im lặng" ở góc nhìn của mắt (bằng chứng render
              2026-07-27: DOM có chữ nhưng màn hình không hiện).
            -->
            <div class="max-h-52 overflow-y-auto">
              <!-- Empty state -->
              <div
                v-if="!loading && results.length === 0"
                class="px-3 py-4 text-sm text-slate-400 text-center"
              >
                Không tìm thấy người dùng nào
              </div>

              <!-- Results -->
              <button
                v-for="(user, idx) in results"
                :key="user.name"
                type="button"
                class="w-full text-left px-3 py-2.5 border-b border-slate-50 last:border-0 transition-colors flex items-center gap-2.5"
                :class="idx === highlighted ? 'bg-blue-50' : 'hover:bg-slate-50'"
                @mousedown.prevent="selectUser(user)"
              >
                <img
                  v-if="user.user_image"
                  :src="user.user_image"
                  class="w-7 h-7 rounded-full object-cover shrink-0"
                  :alt="displayName(user)"
                />
                <div
                  v-else
                  class="w-7 h-7 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center text-xs font-bold shrink-0"
                >
                  {{ displayName(user).charAt(0).toUpperCase() }}
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ displayName(user) }}</p>
                  <p class="text-xs text-slate-500 truncate">{{ user.email || user.name }}</p>
                </div>
              </button>
            </div>

            <!--
              AC-CR-80: danh sách bị cắt ở `limit` phải NÓI RA. Không có dải này
              thì người dùng tin "chỉ có bấy nhiêu người đủ năng lực" (cắt im lặng).
              Chỉ render khi truncated === 1 — không để dải rỗng chiếm chỗ.
            -->
            <p
              v-if="truncated === 1"
              role="status"
              class="px-3 py-2 text-xs text-amber-800 bg-amber-50 border-t border-amber-200"
            >
              Đang hiển thị {{ results.length }}/{{ total }} người — gõ tên để tìm thêm
            </p>
          </div>
        </Transition>
      </template>
    </div>
  </div>
</template>
