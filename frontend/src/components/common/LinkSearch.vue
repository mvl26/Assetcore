<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import api from '@/api/axios'

interface LinkItem {
  value: string
  label: string
  description: string
}

const props = defineProps<{
  modelValue: string
  doctype: 'Purchase Order' | 'Item' | 'Supplier' | 'Department' | 'User'
  placeholder?: string
  disabled?: boolean
  hasError?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'select': [item: LinkItem]
  'blur': []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const query = ref(props.modelValue)
const results = ref<LinkItem[]>([])
const open = ref(false)
const loading = ref(false)
const activeIndex = ref(-1)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(() => props.modelValue, (val) => {
  if (val !== query.value) query.value = val
})

async function doSearch(q: string) {
  loading.value = true
  try {
    const res = await api.get('/api/method/assetcore.api.imm04.search_link', {
      params: { doctype: props.doctype, query: q, page_length: 10 },
    })
    const envelope = res.data?.message ?? res.data
    if (envelope?.success && Array.isArray(envelope.data)) {
      results.value = envelope.data
    } else {
      results.value = []
    }
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}

function onInput() {
  emit('update:modelValue', query.value)
  open.value = true
  activeIndex.value = -1
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => doSearch(query.value), 250)
}

function onFocus() {
  open.value = true
  if (!results.value.length) doSearch(query.value)
}

function selectItem(item: LinkItem) {
  query.value = item.value
  emit('update:modelValue', item.value)
  emit('select', item)
  open.value = false
  results.value = []
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
  }
}

function onClickOutside(e: MouseEvent) {
  if (inputRef.value && !inputRef.value.closest('.link-search-wrapper')?.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div class="link-search-wrapper relative">
    <div class="relative">
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
        @blur="emit('blur')"
        @keydown="onKeydown"
      />
      <span class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
        <svg v-if="loading" class="w-3.5 h-3.5 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <svg v-else class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </span>
    </div>

    <!-- Dropdown -->
    <ul
      v-if="open && results.length"
      class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto"
    >
      <li
        v-for="(item, idx) in results"
        :key="item.value"
        class="flex flex-col px-3 py-2 cursor-pointer text-sm"
        :class="idx === activeIndex ? 'bg-blue-50 text-blue-800' : 'hover:bg-gray-50'"
        @mousedown.prevent="selectItem(item)"
      >
        <span class="font-medium">{{ item.value }}</span>
        <span v-if="item.label !== item.value || item.description" class="text-xs text-gray-500 truncate">
          {{ [item.label !== item.value ? item.label : '', item.description].filter(Boolean).join(' — ') }}
        </span>
      </li>
    </ul>

    <!-- No results hint -->
    <div
      v-if="open && !loading && results.length === 0 && query.length > 0"
      class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-sm px-3 py-2 text-sm text-gray-400"
    >
      Không tìm thấy kết quả
    </div>
  </div>
</template>
