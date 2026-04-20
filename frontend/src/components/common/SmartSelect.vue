<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// SmartSelect — autocomplete dropdown dùng cache Master Data (Pinia).
//
// UX:
//   - Input hiển thị "Tên (ID)" khi đã chọn
//   - Click để mở dropdown → hiển thị toàn bộ master data
//   - Có ô search bên trong dropdown để lọc theo Tên / ID
//   - Phím mũi tên Up/Down + Enter + Escape hoạt động như native select
//   - v-model trả về ID (không phải Tên)
//
// Khác LinkSearch:
//   - LinkSearch: gọi API mỗi lần gõ
//   - SmartSelect: chỉ gọi API 1 lần qua store, sau đó lọc in-memory → instant

import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useMasterDataStore, type MasterItem } from '@/stores/useMasterDataStore'

type DocType =
  | 'AC Asset' | 'AC Department' | 'AC Location' | 'AC Supplier'
  | 'AC Asset Category' | 'IMM Device Model' | 'IMM Calibration Schedule'
  | 'Purchase Order' | 'User'

const props = defineProps<{
  modelValue: string | undefined | null
  doctype: DocType
  placeholder?: string
  disabled?: boolean
  hasError?: boolean
  /** Chiều cao tối đa dropdown (px). Mặc định 320 */
  maxHeight?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'select': [item: MasterItem]
  'clear': []
}>()

const store = useMasterDataStore()

const wrapperRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const open = ref(false)
const searchQuery = ref('')
const activeIndex = ref(-1)

// Resolve item hiển thị từ modelValue (bằng cache)
const selectedItem = computed<MasterItem | null>(() => {
  if (!props.modelValue) return null
  return store.getItemById(props.doctype, props.modelValue) ?? null
})


const allItems = computed<MasterItem[]>(() => store.getItems(props.doctype))

const filteredItems = computed<MasterItem[]>(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return allItems.value
  return allItems.value.filter(it =>
    it.name.toLowerCase().includes(q)
    || it.id.toLowerCase().includes(q)
    || (it.description ?? '').toLowerCase().includes(q),
  )
})

const dropdownStyle = computed(() => ({
  maxHeight: `${props.maxHeight ?? 320}px`,
}))

async function ensureLoaded() {
  if (allItems.value.length === 0) {
    await store.fetchDoctype(props.doctype)
  }
}

async function toggle() {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    await ensureLoaded()
    searchQuery.value = ''
    activeIndex.value = selectedItem.value
      ? filteredItems.value.findIndex(it => it.id === selectedItem.value!.id)
      : 0
    await nextTick()
    searchInputRef.value?.focus()
  }
}

function close() {
  open.value = false
  activeIndex.value = -1
}

function selectItem(item: MasterItem) {
  emit('update:modelValue', item.id)
  emit('select', item)
  close()
}

function clearSelection(e: Event) {
  e.stopPropagation()
  if (props.disabled) return
  emit('update:modelValue', '')
  emit('clear')
  close()
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) return
  const items = filteredItems.value
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, items.length - 1)
    scrollActiveIntoView()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
    scrollActiveIntoView()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (activeIndex.value >= 0 && items[activeIndex.value]) {
      selectItem(items[activeIndex.value])
    }
  } else if (e.key === 'Escape') {
    e.preventDefault()
    close()
  }
}

function scrollActiveIntoView() {
  nextTick(() => {
    const list = wrapperRef.value?.querySelector('[data-smart-list]')
    const el = list?.children[activeIndex.value] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  })
}

function onClickOutside(e: MouseEvent) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) close()
}

// Khi modelValue từ bên ngoài set → đảm bảo đã load cache để resolve label
watch(() => props.modelValue, async (val) => {
  if (val && allItems.value.length === 0) await ensureLoaded()
}, { immediate: true })

// Reset search khi filter mới → focus item đầu
watch(searchQuery, () => { activeIndex.value = filteredItems.value.length > 0 ? 0 : -1 })

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div ref="wrapperRef" class="smart-select relative">
    <!-- Trigger button -->
    <button
      type="button"
      :disabled="disabled"
      class="w-full flex items-center justify-between gap-2 form-input text-left transition-colors"
      :class="[
        hasError ? 'border-red-400' : 'border-slate-300 hover:border-brand-400',
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        open ? 'ring-2 ring-brand-300 border-brand-400' : '',
      ]"
      @click="toggle"
    >
      <span class="flex-1 min-w-0 text-left">
        <span v-if="selectedItem" class="text-sm text-slate-800 truncate block">
          {{ selectedItem.name }}
          <span class="text-[11px] text-slate-400 font-mono ml-1">({{ selectedItem.id }})</span>
        </span>
        <span v-else-if="modelValue" class="text-sm font-mono text-slate-500 truncate block">
          {{ modelValue }}
        </span>
        <span v-else class="text-sm text-slate-400 truncate block">
          {{ placeholder || 'Chọn...' }}
        </span>
      </span>
      <span class="shrink-0 flex items-center gap-1">
        <button
          v-if="modelValue && !disabled"
          type="button"
          class="p-0.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500"
          tabindex="-1"
          aria-label="Xóa"
          @click="clearSelection"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <svg class="w-4 h-4 text-slate-400 transition-transform"
             :class="open ? 'rotate-180' : ''"
             fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </span>
    </button>

    <!-- Dropdown -->
    <div
      v-if="open"
      class="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-xl overflow-hidden"
    >
      <!-- Search inside dropdown -->
      <div class="p-2 border-b border-slate-100 bg-slate-50">
        <div class="relative">
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            class="w-full text-sm border border-slate-200 rounded-md pl-8 pr-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-300"
            placeholder="Tìm theo tên hoặc mã..."
            @keydown="onKeydown"
          />
          <svg class="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400"
               fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="store.isLoading(doctype) && !allItems.length"
           class="px-3 py-4 text-center text-sm text-slate-400">
        <svg class="w-4 h-4 inline-block animate-spin mr-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Đang tải dữ liệu...
      </div>

      <!-- Empty state -->
      <div v-else-if="!filteredItems.length"
           class="px-3 py-6 text-center text-sm text-slate-400">
        <span v-if="searchQuery">Không tìm thấy "{{ searchQuery }}"</span>
        <span v-else>Chưa có dữ liệu {{ doctype }}</span>
      </div>

      <!-- Item list -->
      <ul v-else
          data-smart-list
          class="overflow-y-auto py-1"
          :style="dropdownStyle">
        <li
          v-for="(item, idx) in filteredItems"
          :key="item.id"
          class="flex items-start gap-2.5 px-3 py-2 cursor-pointer text-sm transition-colors"
          :class="[
            idx === activeIndex ? 'bg-brand-50' : 'hover:bg-slate-50',
            selectedItem?.id === item.id ? 'text-brand-700 font-medium' : 'text-slate-700',
          ]"
          @mousedown.prevent="selectItem(item)"
          @mouseenter="activeIndex = idx"
        >
          <!-- Check icon khi đã chọn -->
          <span class="shrink-0 mt-0.5 w-4 h-4 flex items-center justify-center">
            <svg v-if="selectedItem?.id === item.id"
                 class="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <span v-else class="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
          </span>
          <span class="flex-1 min-w-0 flex flex-col">
            <span class="truncate">{{ item.name }}</span>
            <span class="text-[11px] text-slate-400 truncate font-mono">
              {{ item.id }}<span v-if="item.description"> · {{ item.description }}</span>
            </span>
          </span>
        </li>
      </ul>

      <!-- Footer: count -->
      <div v-if="filteredItems.length > 0"
           class="px-3 py-1.5 border-t border-slate-100 text-[11px] text-slate-400 bg-slate-50">
        {{ filteredItems.length }}/{{ allItems.length }} kết quả
      </div>
    </div>
  </div>
</template>
