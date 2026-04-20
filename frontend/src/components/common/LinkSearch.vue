<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import api from '@/api/axios'

interface LinkItem {
  value: string
  label: string
  description: string
}

const props = defineProps<{
  modelValue: string | undefined
  doctype:
    | 'Purchase Order'
    | 'AC Supplier'
    | 'AC Department'
    | 'AC Location'
    | 'AC Asset'
    | 'AC Asset Category'
    | 'IMM Device Model'
    | 'IMM Calibration Schedule'
    | 'User'
  placeholder?: string
  disabled?: boolean
  hasError?: boolean
  /** Hiển thị label thay vì value khi đã chọn (mặc định true) */
  showLabel?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'select': [item: LinkItem]
  'blur': []
  'clear': []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const wrapperRef = ref<HTMLElement | null>(null)
const query = ref('')
const results = ref<LinkItem[]>([])
const open = ref(false)
const loading = ref(false)
const activeIndex = ref(-1)
const editing = ref(false)
const selected = ref<LinkItem | null>(null)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

const showLabelMode = computed(() => props.showLabel !== false)
const isFilled = computed(() => Boolean(props.modelValue) && !editing.value)
const displayLabel = computed(() => selected.value?.label || props.modelValue)
const displayDesc = computed(() => selected.value?.description || '')

watch(() => props.modelValue, (val) => {
  if (!val) {
    selected.value = null
    query.value = ''
  } else if (val !== query.value && val !== selected.value?.value) {
    // External change — try resolve label by quick fetch
    query.value = val
    fetchSelectedDetails(val)
  }
}, { immediate: true })

async function fetchSelectedDetails(value: string) {
  try {
    const res = await api.get('/api/method/assetcore.api.imm04.search_link', {
      params: { doctype: props.doctype, query: value, page_length: 5 },
    })
    const envelope = res.data?.message ?? res.data
    if (envelope?.success && Array.isArray(envelope.data)) {
      const match = envelope.data.find((it: LinkItem) => it.value === value)
      if (match) selected.value = match
    }
  } catch { /* ignore */ }
}

async function doSearch(q: string) {
  loading.value = true
  try {
    const res = await api.get('/api/method/assetcore.api.imm04.search_link', {
      params: { doctype: props.doctype, query: q, page_length: 10 },
    })
    const envelope = res.data?.message ?? res.data
    results.value = envelope?.success && Array.isArray(envelope.data) ? envelope.data : []
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}

function startEdit() {
  if (props.disabled) return
  editing.value = true
  query.value = ''
  open.value = true
  doSearch('')
  // Focus next tick
  setTimeout(() => inputRef.value?.focus(), 0)
}

function onInput() {
  emit('update:modelValue', query.value)
  selected.value = null
  open.value = true
  activeIndex.value = -1
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => doSearch(query.value), 250)
}

function onFocus() {
  editing.value = true
  open.value = true
  if (!results.value.length) doSearch(query.value)
}

function onBlur() {
  // Delay to allow click on dropdown to register
  setTimeout(() => {
    editing.value = false
    emit('blur')
  }, 200)
}

function selectItem(item: LinkItem) {
  selected.value = item
  query.value = item.value
  emit('update:modelValue', item.value)
  emit('select', item)
  open.value = false
  editing.value = false
  results.value = []
}

function clearSelection() {
  if (props.disabled) return
  selected.value = null
  query.value = ''
  emit('update:modelValue', '')
  emit('clear')
  startEdit()
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, results.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
  } else if (e.key === 'Enter' && activeIndex.value >= 0) {
    e.preventDefault()
    selectItem(results.value[activeIndex.value])
  } else if (e.key === 'Escape') {
    open.value = false
    editing.value = false
    inputRef.value?.blur()
  }
}

function onClickOutside(e: MouseEvent) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    open.value = false
    editing.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onClickOutside)
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <div ref="wrapperRef" class="link-search-wrapper relative">
    <!-- Selected display (chip mode) -->
    <button
      v-if="isFilled && showLabelMode"
      type="button"
      :disabled="disabled"
      class="w-full flex items-center justify-between gap-2 form-input text-left transition-colors"
      :class="[
        hasError ? 'border-red-400' : 'border-slate-300 hover:border-brand-400',
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
      ]"
      @click="startEdit"
    >
      <span class="flex-1 min-w-0 flex flex-col">
        <span class="text-sm font-medium text-slate-800 truncate">{{ displayLabel }}</span>
        <span class="text-[11px] text-slate-400 truncate font-mono">
          {{ modelValue }}<span v-if="displayDesc"> · {{ displayDesc }}</span>
        </span>
      </span>
      <span
        v-if="!disabled"
        class="shrink-0 p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
        @click.stop="clearSelection"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </span>
    </button>

    <!-- Edit mode (input) -->
    <div v-else class="relative">
      <input
        ref="inputRef"
        v-model="query"
        type="text"
        class="form-input pr-8"
        :class="{ 'border-red-400 focus:ring-red-300': hasError }"
        :placeholder="placeholder"
        :disabled="disabled"
        autocomplete="off"
        @input="onInput"
        @focus="onFocus"
        @blur="onBlur"
        @keydown="onKeydown"
      />
      <span class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
        <svg v-if="loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </span>
    </div>

    <!-- Dropdown -->
    <ul
      v-if="open && results.length"
      class="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-72 overflow-y-auto"
    >
      <li
        v-for="(item, idx) in results"
        :key="item.value"
        class="flex items-start gap-3 px-3 py-2.5 cursor-pointer text-sm transition-colors"
        :class="idx === activeIndex ? 'bg-brand-50' : 'hover:bg-slate-50'"
        @mousedown.prevent="selectItem(item)"
        @mouseenter="activeIndex = idx"
      >
        <span class="shrink-0 mt-0.5 inline-flex items-center justify-center w-6 h-6 rounded bg-slate-100 text-slate-500">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0L4.929 13.414a4 4 0 105.657 5.657l1.06-1.06m-1.06-9.9a4 4 0 015.656 0l3.243 3.243a4 4 0 11-5.657 5.657l-1.06-1.06" />
          </svg>
        </span>
        <span class="flex-1 min-w-0 flex flex-col">
          <span class="font-medium text-slate-800 truncate">{{ item.label || item.value }}</span>
          <span class="text-[11px] text-slate-400 truncate font-mono">
            {{ item.value }}<span v-if="item.description"> · {{ item.description }}</span>
          </span>
        </span>
      </li>
    </ul>

    <!-- No results hint -->
    <div
      v-if="open && !loading && results.length === 0 && (query.length > 0 || editing)"
      class="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-sm px-3 py-2.5 text-sm text-slate-400"
    >
      <span v-if="query.length > 0">Không tìm thấy kết quả cho "{{ query }}"</span>
      <span v-else>Bắt đầu nhập để tìm...</span>
    </div>
  </div>
</template>
