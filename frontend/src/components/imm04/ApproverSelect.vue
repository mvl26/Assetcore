<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { getUsersByRole } from '@/api/imm04'

// ─── Props & Emits ────────────────────────────────────────────────────────────

interface Props {
  modelValue: string
  role: string
  label?: string
  placeholder?: string
  disabled?: boolean
  required?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  label: '',
  placeholder: 'Tìm theo tên hoặc email...',
  disabled: false,
  required: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// ─── State ────────────────────────────────────────────────────────────────────

interface UserOption {
  name: string
  full_name: string
  email: string
  user_image?: string
}

const query       = ref('')
const results     = ref<UserOption[]>([])
const loading     = ref(false)
const open        = ref(false)
const highlighted = ref(-1)
const inputRef    = ref<HTMLInputElement | null>(null)
const selectedUser = ref<UserOption | null>(null)

// ─── Debounce search ──────────────────────────────────────────────────────────

let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function doSearch(q: string) {
  loading.value = true
  try {
    const rows = await getUsersByRole(props.role, q, 20)
    results.value = rows
  } catch {
    results.value = []
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
    const rows = await getUsersByRole(props.role, '', 50)
    const found = rows.find(r => r.name === username)
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
          :alt="selectedUser.full_name"
        />
        <div
          v-else
          class="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
        >
          {{ (selectedUser.full_name || selectedUser.name).charAt(0).toUpperCase() }}
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-800 truncate">{{ selectedUser.full_name || selectedUser.name }}</p>
          <p class="text-xs text-slate-500 truncate">{{ selectedUser.email || selectedUser.name }}</p>
        </div>

        <!-- Clear button -->
        <button
          v-if="!disabled"
          type="button"
          class="shrink-0 text-slate-400 hover:text-red-500 transition-colors mt-0.5"
          @click="clearSelection"
          aria-label="Xóa lựa chọn"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Search input when no user selected -->
      <template v-else>
        <input
          ref="inputRef"
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
            class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-52 overflow-y-auto z-20"
          >
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
                :alt="user.full_name"
              />
              <div
                v-else
                class="w-7 h-7 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center text-xs font-bold shrink-0"
              >
                {{ user.full_name.charAt(0).toUpperCase() }}
              </div>
              <div class="min-w-0">
                <p class="text-sm font-medium text-slate-800 truncate">{{ user.full_name }}</p>
                <p class="text-xs text-slate-500 truncate">{{ user.email }}</p>
              </div>
            </button>
          </div>
        </Transition>
      </template>
    </div>
  </div>
</template>
